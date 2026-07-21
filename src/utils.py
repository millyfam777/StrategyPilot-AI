"""Formatting and export helpers shared by the application."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any


def format_currency(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    formatted = f"${abs(value):,.2f}"
    return f"-{formatted}" if value < 0 else formatted


def format_ratio(value: float | None) -> str:
    if value is None:
        return "N/A"
    if math.isinf(value):
        return "∞"
    return f"{value:.2f}"


def format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def format_evidence_value(kind: str, value: Any) -> str:
    if kind == "currency":
        return format_currency(value)
    if kind == "percent":
        return format_percent(value)
    if kind == "ratio":
        return format_ratio(value)
    return str(value)


def audit_to_markdown(
    metrics: dict[str, Any], findings: list[dict[str, str]], source_label: str, audit_mode: str
) -> str:
    """Render a portable Markdown audit report."""

    lines = [
        "# StrategyPilot AI — Engineering Audit",
        "",
        f"- Data source: {source_label}",
        f"- Audit mode: {audit_mode}",
        f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Deterministic evidence",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Complete setups | {metrics['complete_setups']} |",
        f"| Setup win rate | {format_percent(metrics['setup_win_rate'])} |",
        f"| Net profit | {format_currency(metrics['net_profit'])} |",
        f"| Gross profit | {format_currency(metrics['gross_profit'])} |",
        f"| Gross loss magnitude | {format_currency(metrics['gross_loss'])} |",
        f"| Profit factor | {format_ratio(metrics['profit_factor'])} |",
        f"| Expectancy | {format_currency(metrics['expectancy'])} |",
        f"| Maximum drawdown magnitude | {format_currency(metrics['maximum_drawdown'])} |",
        f"| Average winner | {format_currency(metrics['average_winner'])} |",
        f"| Average loser | {format_currency(metrics['average_loser'])} |",
        f"| Win/loss ratio | {format_ratio(metrics['win_loss_ratio'])} |",
        "",
        "## Engineering findings",
        "",
    ]
    for index, finding in enumerate(findings, 1):
        lines.extend([
            f"### {index}. [{finding['priority']}] {finding['finding']}",
            "",
            f"**Evidence:** {finding['evidence']}",
            "",
            f"**Engineering task:** {finding['engineering_task']}",
            "",
            f"**Regression check:** {finding['regression_check']}",
            "",
        ])
    lines.extend([
        "---",
        "",
        "StrategyPilot AI is an engineering audit tool. This report is for informational and software-testing purposes only; it is not financial advice or a prediction of future results.",
    ])
    return "\n".join(lines)
