from io import StringIO

import pandas as pd
import pytest

from src.parser import ValidationError, parse_csv


def test_parser_normalizes_aliases_and_direction() -> None:
    result = parse_csv(StringIO("timestamp,side,profit_loss\n2026-01-01T10:00:00Z,buy,12.5\n"))
    assert list(result.data["direction"]) == ["Long"]
    assert result.data.loc[0, "pnl"] == 12.5
    assert result.data.loc[0, "setup_id"] == result.data.loc[0, "trade_id"]
    assert any("setup_id" in warning for warning in result.warnings)


def test_parser_rejects_missing_required_column() -> None:
    with pytest.raises(ValidationError, match="pnl"):
        parse_csv(StringIO("entry_time,direction\n2026-01-01,long\n"))


def test_parser_rejects_bad_timestamp() -> None:
    with pytest.raises(ValidationError, match="entry_time"):
        parse_csv(StringIO("entry_time,direction,pnl\nnot-a-date,long,10\n"))


def test_parser_rejects_bad_direction() -> None:
    with pytest.raises(ValidationError, match="direction"):
        parse_csv(StringIO("entry_time,direction,pnl\n2026-01-01,flat,10\n"))


def test_parser_coerces_optional_numeric_and_preserves_shape() -> None:
    result = parse_csv(StringIO("entry_time,direction,pnl,mae,mfe\n2026-01-01,sell,-4,bad,9\n"))
    assert result.data.loc[0, "direction"] == "Short"
    assert pd.isna(result.data.loc[0, "mae"])
    assert result.data.loc[0, "mfe"] == 9
