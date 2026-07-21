"""Deterministic setup reconstruction and performance calculations."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


def _consistent_label(values: pd.Series) -> str:
    labels = [str(value) for value in values.dropna().unique()]
    return labels[0] if len(labels) == 1 else "Mixed"


def reconstruct_setups(trades: pd.DataFrame) -> pd.DataFrame:
    """Collapse trade legs into complete setups before performance analysis."""

    if trades.empty:
        return pd.DataFrame(
            columns=["setup_id", "entry_time", "direction", "session", "symbol", "pnl", "trade_legs"]
        )
    setups = (
        trades.groupby("setup_id", sort=False, dropna=False)
        .agg(
            entry_time=("entry_time", "min"),
            direction=("direction", _consistent_label),
            session=("session", _consistent_label),
            symbol=("symbol", _consistent_label),
            pnl=("pnl", "sum"),
            trade_legs=("trade_id", "size"),
        )
        .reset_index()
        .sort_values(["entry_time", "setup_id"], kind="stable")
        .reset_index(drop=True)
    )
    setups["outcome"] = setups["pnl"].map(lambda value: "Win" if value > 0 else "Loss" if value < 0 else "Breakeven")
    setups["equity"] = setups["pnl"].cumsum()
    setups["equity_peak"] = setups["equity"].cummax().clip(lower=0)
    setups["drawdown"] = setups["equity"] - setups["equity_peak"]
    return setups


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return math.inf if numerator > 0 else None
    return numerator / denominator


def _group_performance(setups: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, group in setups.groupby(column, sort=True, dropna=False):
        count = len(group)
        wins = int((group["pnl"] > 0).sum())
        rows.append(
            {
                column: str(label),
                "setups": count,
                "wins": wins,
                "win_rate": wins / count if count else 0.0,
                "net_profit": float(group["pnl"].sum()),
                "expectancy": float(group["pnl"].mean()),
            }
        )
    return rows


def calculate_metrics(trades: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    """Calculate all product metrics at reconstructed setup granularity."""

    setups = reconstruct_setups(trades)
    if setups.empty:
        raise ValueError("At least one complete setup is required.")

    winners = setups.loc[setups["pnl"] > 0, "pnl"]
    losers = setups.loc[setups["pnl"] < 0, "pnl"]
    gross_profit = float(winners.sum())
    gross_loss = float(-losers.sum())
    average_winner = float(winners.mean()) if not winners.empty else 0.0
    average_loser = float(losers.mean()) if not losers.empty else 0.0
    metrics: dict[str, Any] = {
        "complete_setups": len(setups),
        "winning_setups": int((setups["pnl"] > 0).sum()),
        "losing_setups": int((setups["pnl"] < 0).sum()),
        "breakeven_setups": int((setups["pnl"] == 0).sum()),
        "setup_win_rate": float((setups["pnl"] > 0).mean()),
        "net_profit": float(setups["pnl"].sum()),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": _ratio(gross_profit, gross_loss),
        "expectancy": float(setups["pnl"].mean()),
        "maximum_drawdown": float(-setups["drawdown"].min()),
        "average_winner": average_winner,
        "average_loser": average_loser,
        "win_loss_ratio": _ratio(average_winner, abs(average_loser)),
        "direction_performance": _group_performance(setups, "direction"),
        "session_performance": _group_performance(setups, "session"),
    }
    return metrics, setups
