from io import StringIO

from src.audit import build_evidence_catalog, build_evidence_payload, generate_audit
from src.metrics import calculate_metrics
from src.parser import parse_csv


def _payload():
    trades = parse_csv(StringIO(
        "entry_time,direction,pnl,session\n"
        "2026-01-01,long,20,New York\n"
        "2026-01-02,short,-10,London\n"
        "2026-01-03,long,15,London\n"
    )).data
    metrics, _ = calculate_metrics(trades)
    return build_evidence_payload(metrics)


def test_evidence_payload_contains_aggregates_only() -> None:
    payload = _payload()
    assert set(payload) == {"overview", "direction_performance", "session_performance"}
    serialized = str(payload)
    assert "trade_id" not in serialized
    assert "entry_time" not in serialized


def test_demo_audit_has_complete_structured_findings() -> None:
    result = generate_audit(_payload(), api_key=None)
    assert result.mode == "Deterministic Demo Audit"
    assert 3 <= len(result.findings) <= 5
    for finding in result.findings:
        assert set(finding) == {"finding", "evidence", "engineering_task", "regression_check", "priority"}
        assert finding["priority"] in {"High", "Medium", "Low"}


def test_catalog_values_are_verified_payload_values() -> None:
    payload = _payload()
    catalog = build_evidence_catalog(payload)
    assert catalog["overview.net_profit"]["value"] == payload["overview"]["net_profit"]
