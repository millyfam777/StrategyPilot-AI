from io import StringIO

import math
import pytest

from src.metrics import calculate_metrics, reconstruct_setups
from src.parser import parse_csv


CSV = """trade_id,setup_id,entry_time,direction,pnl,session
1,A,2026-01-01T10:00:00Z,Long,50,New York
2,A,2026-01-01T10:00:00Z,Long,25,New York
3,B,2026-01-02T10:00:00Z,Short,-40,London
4,C,2026-01-03T10:00:00Z,Long,10,London
5,C,2026-01-03T10:00:00Z,Long,-10,London
6,D,2026-01-04T10:00:00Z,Short,20,New York
"""


def _data():
    return parse_csv(StringIO(CSV)).data


def test_reconstructs_trade_legs_before_counting() -> None:
    setups = reconstruct_setups(_data())
    assert len(setups) == 4
    assert setups.loc[setups["setup_id"] == "A", "pnl"].item() == 75
    assert setups.loc[setups["setup_id"] == "C", "outcome"].item() == "Breakeven"


def test_core_metrics_are_setup_level() -> None:
    metrics, _ = calculate_metrics(_data())
    assert metrics["complete_setups"] == 4
    assert metrics["setup_win_rate"] == pytest.approx(0.5)
    assert metrics["net_profit"] == pytest.approx(55)
    assert metrics["gross_profit"] == pytest.approx(95)
    assert metrics["gross_loss"] == pytest.approx(40)
    assert metrics["profit_factor"] == pytest.approx(2.375)
    assert metrics["expectancy"] == pytest.approx(13.75)


def test_drawdown_uses_chronological_setup_equity() -> None:
    metrics, setups = calculate_metrics(_data())
    assert list(setups["equity"]) == [75, 35, 35, 55]
    assert metrics["maximum_drawdown"] == pytest.approx(40)


def test_average_and_win_loss_metrics() -> None:
    metrics, _ = calculate_metrics(_data())
    assert metrics["average_winner"] == pytest.approx(47.5)
    assert metrics["average_loser"] == pytest.approx(-40)
    assert metrics["win_loss_ratio"] == pytest.approx(1.1875)


def test_profit_factor_is_infinite_without_losses() -> None:
    data = parse_csv(StringIO("entry_time,direction,pnl\n2026-01-01,long,10\n")).data
    metrics, _ = calculate_metrics(data)
    assert math.isinf(metrics["profit_factor"])


def test_group_performance_reconciles_to_total() -> None:
    metrics, _ = calculate_metrics(_data())
    assert sum(row["setups"] for row in metrics["direction_performance"]) == metrics["complete_setups"]
    assert sum(row["net_profit"] for row in metrics["session_performance"]) == pytest.approx(metrics["net_profit"])
