"""CSV validation and normalization for trading-result exports."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import BinaryIO, TextIO, Union

import pandas as pd

CANONICAL_COLUMNS = [
    "trade_id",
    "setup_id",
    "entry_time",
    "direction",
    "pnl",
    "session",
    "symbol",
    "exit_reason",
    "mae",
    "mfe",
]
REQUIRED_COLUMNS = {"entry_time", "direction", "pnl"}
ALIASES = {
    "timestamp": "entry_time",
    "entry_datetime": "entry_time",
    "entry_date": "entry_time",
    "side": "direction",
    "profit_loss": "pnl",
    "profit": "pnl",
    "p_l": "pnl",
    "ticker": "symbol",
}


class ValidationError(ValueError):
    """Raised when an input file cannot be safely normalized."""


@dataclass(frozen=True)
class ParseResult:
    """Normalized data plus user-facing validation notes."""

    data: pd.DataFrame
    warnings: tuple[str, ...]


CsvSource = Union[str, bytes, bytearray, BinaryIO, TextIO]


def _normalize_name(name: object) -> str:
    normalized = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    return ALIASES.get(normalized, normalized)


def _read_csv(source: CsvSource) -> pd.DataFrame:
    if isinstance(source, str):
        buffer: Union[StringIO, BytesIO] = StringIO(source)
    elif isinstance(source, (bytes, bytearray)):
        buffer = BytesIO(bytes(source))
    else:
        buffer = source
    try:
        return pd.read_csv(buffer)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise ValidationError(f"Could not read CSV: {exc}") from exc


def parse_csv(source: CsvSource) -> ParseResult:
    """Read, validate, and normalize a StrategyPilot-compatible CSV.

    Missing ``trade_id`` values are generated deterministically. Missing
    ``setup_id`` values fall back to ``trade_id`` so every row belongs to one
    complete reconstructed setup.
    """

    frame = _read_csv(source)
    if frame.empty:
        raise ValidationError("The CSV contains no trade rows.")

    normalized_names = [_normalize_name(column) for column in frame.columns]
    if len(normalized_names) != len(set(normalized_names)):
        raise ValidationError("Column names collide after normalization.")
    frame.columns = normalized_names

    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValidationError("Missing required columns: " + ", ".join(missing))

    frame = frame.dropna(how="all").copy()
    if frame.empty:
        raise ValidationError("The CSV contains no non-empty trade rows.")

    warnings: list[str] = []
    parsed_times = pd.to_datetime(frame["entry_time"], errors="coerce", utc=True)
    invalid_times = parsed_times.isna()
    if invalid_times.any():
        rows = (frame.index[invalid_times] + 2).tolist()[:5]
        raise ValidationError(f"Invalid entry_time value on CSV row(s): {rows}")
    frame["entry_time"] = parsed_times

    parsed_pnl = pd.to_numeric(frame["pnl"], errors="coerce")
    invalid_pnl = parsed_pnl.isna()
    if invalid_pnl.any():
        rows = (frame.index[invalid_pnl] + 2).tolist()[:5]
        raise ValidationError(f"Invalid pnl value on CSV row(s): {rows}")
    frame["pnl"] = parsed_pnl.astype(float)

    directions = frame["direction"].astype("string").str.strip().str.lower()
    directions = directions.replace({"buy": "long", "sell": "short", "l": "long", "s": "short"})
    invalid_directions = ~directions.isin(["long", "short"])
    if invalid_directions.any():
        values = sorted(frame.loc[invalid_directions, "direction"].astype(str).unique())
        raise ValidationError("direction must be long/short (or buy/sell). Invalid: " + ", ".join(values))
    frame["direction"] = directions.str.title()

    if "trade_id" not in frame:
        frame["trade_id"] = pd.NA
    trade_ids = frame["trade_id"].astype("string").str.strip()
    missing_trade_ids = trade_ids.isna() | trade_ids.eq("")
    generated = pd.Series(
        [f"trade_{position + 1:06d}" for position in range(len(frame))],
        index=frame.index,
        dtype="string",
    )
    frame["trade_id"] = trade_ids.mask(missing_trade_ids, generated)
    if missing_trade_ids.any():
        warnings.append(f"Generated {int(missing_trade_ids.sum())} missing trade_id value(s).")

    if "setup_id" not in frame:
        frame["setup_id"] = pd.NA
    setup_ids = frame["setup_id"].astype("string").str.strip()
    missing_setup_ids = setup_ids.isna() | setup_ids.eq("")
    frame["setup_id"] = setup_ids.mask(missing_setup_ids, frame["trade_id"])
    if missing_setup_ids.any():
        warnings.append(f"Used trade_id for {int(missing_setup_ids.sum())} missing setup_id value(s).")

    for column in ("session", "symbol", "exit_reason"):
        if column not in frame:
            frame[column] = "Unknown"
        values = frame[column].astype("string").str.strip()
        frame[column] = values.mask(values.isna() | values.eq(""), "Unknown")

    for column in ("mae", "mfe"):
        if column not in frame:
            frame[column] = float("nan")
            continue
        original_nonempty = frame[column].notna() & frame[column].astype(str).str.strip().ne("")
        parsed = pd.to_numeric(frame[column], errors="coerce")
        invalid_count = int((original_nonempty & parsed.isna()).sum())
        if invalid_count:
            warnings.append(f"Coerced {invalid_count} invalid {column} value(s) to missing.")
        frame[column] = parsed.astype(float)

    unknown = [column for column in frame.columns if column not in CANONICAL_COLUMNS]
    if unknown:
        warnings.append("Ignored non-canonical columns: " + ", ".join(unknown))

    frame = frame[CANONICAL_COLUMNS].sort_values("entry_time", kind="stable").reset_index(drop=True)
    return ParseResult(data=frame, warnings=tuple(warnings))
