"""Evidence payloads, deterministic demo findings, and OpenAI audit generation."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from .utils import format_evidence_value

PRIORITIES = {"High", "Medium", "Low"}
NUMBER_PATTERN = re.compile(r"\d")


@dataclass(frozen=True)
class AuditResult:
    findings: list[dict[str, str]]
    mode: str
    notice: str


def _safe_number(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, float):
        return round(value, 6)
    return value


def build_evidence_payload(metrics: dict[str, Any]) -> dict[str, Any]:
    """Create the only aggregate evidence supplied to the model."""

    overview_keys = [
        "complete_setups", "winning_setups", "losing_setups", "breakeven_setups",
        "setup_win_rate", "net_profit", "gross_profit", "gross_loss", "profit_factor",
        "expectancy", "maximum_drawdown", "average_winner", "average_loser", "win_loss_ratio",
    ]
    return {
        "overview": {key: _safe_number(metrics[key]) for key in overview_keys},
        "direction_performance": [
            {key: _safe_number(value) for key, value in row.items()}
            for row in metrics["direction_performance"]
        ],
        "session_performance": [
            {key: _safe_number(value) for key, value in row.items()}
            for row in metrics["session_performance"]
        ],
    }


def build_evidence_catalog(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Flatten verified evidence into stable keys the model may cite."""

    labels = {
        "complete_setups": ("Complete setups", "count"),
        "winning_setups": ("Winning setups", "count"),
        "losing_setups": ("Losing setups", "count"),
        "breakeven_setups": ("Breakeven setups", "count"),
        "setup_win_rate": ("Setup win rate", "percent"),
        "net_profit": ("Net profit", "currency"),
        "gross_profit": ("Gross profit", "currency"),
        "gross_loss": ("Gross loss", "currency"),
        "profit_factor": ("Profit factor", "ratio"),
        "expectancy": ("Expectancy", "currency"),
        "maximum_drawdown": ("Maximum drawdown", "currency"),
        "average_winner": ("Average winner", "currency"),
        "average_loser": ("Average loser", "currency"),
        "win_loss_ratio": ("Win/loss ratio", "ratio"),
    }
    catalog: dict[str, dict[str, Any]] = {}
    for key, value in payload["overview"].items():
        label, kind = labels[key]
        catalog[f"overview.{key}"] = {"label": label, "value": value, "kind": kind}
    for group_key, category_key in (("direction_performance", "direction"), ("session_performance", "session")):
        for row in payload[group_key]:
            category = str(row[category_key])
            prefix = f"{group_key}.{category}"
            for metric, kind in (("setups", "count"), ("win_rate", "percent"), ("net_profit", "currency"), ("expectancy", "currency")):
                catalog[f"{prefix}.{metric}"] = {
                    "label": f"{category} {metric.replace('_', ' ')}",
                    "value": row[metric],
                    "kind": kind,
                }
    return catalog


def _render_evidence(keys: list[str], catalog: dict[str, dict[str, Any]]) -> str:
    parts = []
    for key in keys:
        item = catalog[key]
        parts.append(f"{item['label']}: {format_evidence_value(item['kind'], item['value'])}")
    return "; ".join(parts)


def _finding(
    title: str, keys: list[str], task: str, check: str, priority: str,
    catalog: dict[str, dict[str, Any]],
) -> dict[str, str]:
    return {
        "finding": title,
        "evidence": _render_evidence(keys, catalog),
        "engineering_task": task,
        "regression_check": check,
        "priority": priority,
    }


def demo_audit(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Generate useful, deterministic findings without an API key."""

    catalog = build_evidence_catalog(payload)
    overview = payload["overview"]
    findings: list[dict[str, str]] = []
    expectancy_priority = "High" if (overview["expectancy"] or 0) <= 0 else "Medium"
    findings.append(_finding(
        "Protect the setup-level expectancy baseline",
        ["overview.expectancy", "overview.profit_factor", "overview.complete_setups"],
        "Add the reconstructed-setup metric snapshot to the strategy test harness and require every candidate change to report its delta.",
        "Replay the same fixture and assert that setup aggregation and the saved expectancy baseline remain unchanged.",
        expectancy_priority, catalog,
    ))
    findings.append(_finding(
        "Make drawdown an explicit release guardrail",
        ["overview.maximum_drawdown", "overview.net_profit"],
        "Add a drawdown regression gate beside net profit so a change cannot pass by hiding a materially worse equity path.",
        "Run the chronological setup sequence and fail when drawdown degrades beyond the approved baseline tolerance.",
        "High" if overview["maximum_drawdown"] and overview["maximum_drawdown"] > abs(overview["net_profit"] or 0) else "Medium",
        catalog,
    ))

    directions = payload["direction_performance"]
    if len(directions) >= 2:
        best = max(directions, key=lambda row: row["expectancy"])
        worst = min(directions, key=lambda row: row["expectancy"])
        findings.append(_finding(
            "Investigate direction asymmetry before changing shared logic",
            [f"direction_performance.{best['direction']}.expectancy", f"direction_performance.{worst['direction']}.expectancy"],
            "Instrument direction-specific decision paths and isolate any shared filters whose behavior differs between long and short setups.",
            "Replay direction-tagged fixtures and compare each direction with its own approved expectancy baseline.",
            "High" if worst["expectancy"] < 0 else "Medium", catalog,
        ))

    sessions = payload["session_performance"]
    if sessions:
        worst_session = min(sessions, key=lambda row: row["expectancy"])
        findings.append(_finding(
            "Turn session performance into a diagnostic slice",
            [f"session_performance.{worst_session['session']}.expectancy", f"session_performance.{worst_session['session']}.setups"],
            "Add session labels to experiment reports and require proposed timing changes to show setup-level results by session.",
            "Replay the fixture with session grouping enabled and assert that counts reconcile exactly to complete setups.",
            "Medium", catalog,
        ))
    return findings[:5]


def _schema(catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array", "minItems": 3, "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "finding": {"type": "string"},
                        "evidence_keys": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"type": "string", "enum": list(catalog)}},
                        "engineering_task": {"type": "string"},
                        "regression_check": {"type": "string"},
                        "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                    },
                    "required": ["finding", "evidence_keys", "engineering_task", "regression_check", "priority"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["findings"],
        "additionalProperties": False,
    }


def generate_audit(payload: dict[str, Any], api_key: str | None, model: str = "gpt-5.6-sol") -> AuditResult:
    """Generate an AI audit, or a clearly labeled deterministic fallback."""

    if not api_key:
        return AuditResult(demo_audit(payload), "Deterministic Demo Audit", "No API key detected; verified rule-based findings are shown.")

    catalog = build_evidence_catalog(payload)
    prompt = (
        "Act as a trading-system engineering auditor, not a financial adviser. "
        "Return three to five prioritized engineering findings based only on the JSON evidence. "
        "Cite evidence only through evidence_keys from the supplied catalog. Never calculate, infer, "
        "estimate, or write numeric values in finding, engineering_task, or regression_check; the host "
        "renders every statistic deterministically. Focus on testable software changes, data quality, "
        "instrumentation, and regression protection. Do not recommend trades or predict performance.\n\n"
        + json.dumps({"aggregate_evidence": payload, "evidence_catalog": catalog}, separators=(",", ":"), sort_keys=True)
    )
    try:
        response = OpenAI(api_key=api_key).responses.create(
            model=model,
            reasoning={"effort": "low"},
            input=prompt,
            text={
                "verbosity": "low",
                "format": {"type": "json_schema", "name": "strategy_audit", "strict": True, "schema": _schema(catalog)},
            },
        )
        parsed = json.loads(response.output_text)
        findings: list[dict[str, str]] = []
        for item in parsed["findings"]:
            prose = " ".join([item["finding"], item["engineering_task"], item["regression_check"]])
            if NUMBER_PATTERN.search(prose):
                raise ValueError("Model included an unverified numeric claim.")
            keys = item["evidence_keys"]
            if not keys or any(key not in catalog for key in keys) or item["priority"] not in PRIORITIES:
                raise ValueError("Model returned an invalid evidence reference.")
            findings.append(_finding(
                item["finding"], keys, item["engineering_task"], item["regression_check"],
                item["priority"], catalog,
            ))
        if not 3 <= len(findings) <= 5:
            raise ValueError("Model returned an invalid finding count.")
        return AuditResult(findings, f"AI Audit · {model}", "GPT-5.6 interpretation grounded only in verified aggregate evidence.")
    except Exception as exc:
        return AuditResult(
            demo_audit(payload), "Deterministic Demo Audit",
            f"AI audit unavailable ({type(exc).__name__}); verified rule-based findings are shown.",
        )
