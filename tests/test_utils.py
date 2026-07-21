from src.utils import audit_to_markdown, format_currency, format_evidence_value


def test_format_currency_positive_value() -> None:
    assert format_currency(102.78) == "$102.78"


def test_format_currency_zero_value() -> None:
    assert format_currency(0) == "$0.00"
    assert format_currency(-0.0) == "$0.00"


def test_format_currency_negative_value_places_sign_before_symbol() -> None:
    assert format_currency(-102.78) == "-$102.78"
    assert format_currency(-5) == "-$5.00"


def test_format_currency_handles_missing_value() -> None:
    assert format_currency(None) == "N/A"


def test_audit_evidence_currency_uses_shared_sign_format() -> None:
    assert format_evidence_value("currency", -5) == "-$5.00"
    assert format_evidence_value("currency", 5) == "$5.00"


def test_markdown_preserves_positive_magnitudes_and_signed_average_loser() -> None:
    metrics = {
        "complete_setups": 1,
        "setup_win_rate": 0.0,
        "net_profit": -5.0,
        "gross_profit": 0.0,
        "gross_loss": 5.0,
        "profit_factor": 0.0,
        "expectancy": -5.0,
        "maximum_drawdown": 5.0,
        "average_winner": 0.0,
        "average_loser": -5.0,
        "win_loss_ratio": 0.0,
    }
    report = audit_to_markdown(metrics, [], "fixture.csv", "Demo")
    assert "| Gross loss magnitude | $5.00 |" in report
    assert "| Maximum drawdown magnitude | $5.00 |" in report
    assert "| Average loser | -$5.00 |" in report
