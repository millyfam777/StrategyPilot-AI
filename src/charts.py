"""Plotly chart builders for the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .utils import format_currency

ACCENT = "#63e6be"
POSITIVE = "#3ddc97"
NEGATIVE = "#ff6b6b"
GRID = "rgba(148, 163, 184, 0.14)"


def _style(figure: go.Figure, title: str) -> go.Figure:
    figure.update_layout(
        title={
            "text": title,
            "x": 0.02,
            "xanchor": "left",
            "font": {"color": "#f8fafc", "size": 18},
        },
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.35)",
        font={"family": "Inter, Segoe UI, sans-serif", "color": "#e5edf8"},
        margin={"l": 45, "r": 24, "t": 58, "b": 40},
        hoverlabel={"bgcolor": "#111827"},
        legend={"orientation": "h", "y": 1.08, "x": 1, "xanchor": "right", "font": {"color": "#dbeafe"}},
    )
    axis_text = {"color": "#cbd5e1", "size": 12}
    axis_title = {"color": "#e5edf8", "size": 13}
    figure.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, tickfont=axis_text, title_font=axis_title)
    figure.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, tickfont=axis_text, title_font=axis_title)
    return figure


def equity_curve(setups: pd.DataFrame) -> go.Figure:
    figure = go.Figure(go.Scatter(
        x=setups["entry_time"], y=setups["equity"], mode="lines+markers",
        line={"color": ACCENT, "width": 3}, marker={"size": 6},
        fill="tozeroy", fillcolor="rgba(99,230,190,0.10)", name="Equity",
        customdata=setups["equity"].map(format_currency),
        hovertemplate="%{x}<br>Equity: %{customdata}<extra></extra>",
    ))
    figure.update_yaxes(title_text="Equity ($)")
    return _style(figure, "Cumulative setup equity")


def drawdown_curve(setups: pd.DataFrame) -> go.Figure:
    figure = go.Figure(go.Scatter(
        x=setups["entry_time"], y=setups["drawdown"], mode="lines",
        line={"color": NEGATIVE, "width": 2.5}, fill="tozeroy",
        fillcolor="rgba(255,107,107,0.18)", name="Drawdown",
        customdata=setups["drawdown"].map(format_currency),
        hovertemplate="%{x}<br>Drawdown: %{customdata}<extra></extra>",
    ))
    figure.update_yaxes(title_text="Drawdown ($)")
    return _style(figure, "Drawdown from running peak")


def pnl_distribution(setups: pd.DataFrame) -> go.Figure:
    figure = px.histogram(setups, x="pnl", nbins=min(20, max(6, len(setups) // 2)), color_discrete_sequence=[ACCENT])
    figure.update_traces(hovertemplate="Setup P&L range: %{x}<br>Count: %{y}<extra></extra>")
    figure.add_vline(x=0, line_dash="dash", line_color="#94a3b8")
    figure.update_xaxes(title_text="Setup P&L ($)")
    figure.update_yaxes(title_text="Setup count")
    return _style(figure, "Setup P&L distribution")


def category_performance(rows: list[dict[str, object]], category: str, title: str) -> go.Figure:
    frame = pd.DataFrame(rows)
    colors = [POSITIVE if value >= 0 else NEGATIVE for value in frame["net_profit"]]
    frame["net_display"] = frame["net_profit"].map(format_currency)
    frame["expectancy_display"] = frame["expectancy"].map(format_currency)
    frame["win_rate_display"] = frame["win_rate"].map(lambda value: f"{value:.1%}")
    figure = go.Figure(go.Bar(
        x=frame[category], y=frame["net_profit"], marker_color=colors,
        customdata=frame[["setups", "win_rate_display", "expectancy_display", "net_display"]],
        hovertemplate=("%{x}<br>Net: %{customdata[3]}<br>Setups: %{customdata[0]}"
                       "<br>Win rate: %{customdata[1]}<br>Expectancy: %{customdata[2]}<extra></extra>"),
    ))
    figure.add_hline(y=0, line_color="#64748b")
    figure.update_yaxes(title_text="Net profit ($)")
    return _style(figure, title)
