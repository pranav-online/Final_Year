"""Phase 5 backend pieces: the action card and data freshness behind the new Demand Analysis page."""
import pytest

from services.mandi import decisions
from services.mandi.ingest import _finish, _new_report
from services.mandi.store import SqliteMandiStore


def forecast(p10, p50, p90, confidence="high", origin=2000):
    return {"confidence": confidence, "origin_price": origin,
            "horizons": [{"h_weeks": 1, "target_week": "2026-10-19", "p10": p10, "p50": p50, "p90": p90}]}


def signal(quadrant, urgency=None, reasons=None, weeks=20):
    return {"quadrant": quadrant, "urgency": urgency, "urgency_reasons": reasons or [], "weeks_of_history": weeks}


@pytest.mark.parametrize("p50,action", [(1900, "SELL"), (2100, "HOLD"), (2010, "WATCH")])
def test_forecast_driven_action(p50, action):
    card = decisions.action_card("tomato", signal("balanced"), forecast(p50 - 200, p50, p50 + 200))
    assert card["action"] == action and card["basis"] == "forecast" and card["confidence"] == "high"
    assert card["range_text"].startswith("8 in 10 times") and card["action_window"] == "1-2 days"


def test_insufficient_forecast_falls_back_to_signals_with_low_confidence():
    card = decisions.action_card("onion", signal("glut", 6, ["arrivals 1.60x normal"]),
                                 forecast(1, 2, 3, confidence="insufficient"))
    assert card["action"] == "SELL" and card["confidence"] == "low" and card["basis"] == "signals"
    assert "arrivals 1.60x normal" in card["reason"] and card["action_window"] == "5 days"
    assert decisions.action_card("wheat", signal("supply_shortage"))["action"] == "HOLD"
    assert decisions.action_card("wheat", signal("balanced", urgency=8))["action"] == "SELL"
    assert decisions.action_card("wheat", signal("balanced"))["action_window"] == "14 days"


def test_no_data_says_not_enough_signal():
    card = decisions.action_card("tomato", signal("insufficient_data", weeks=1))
    assert card["action"] == "WATCH" and card["confidence"] == "insufficient"
    assert "1 week(s)" in card["reason"]
    assert decisions.action_card("tomato")["confidence"] == "insufficient"


@pytest.mark.asyncio
async def test_analysis_reports_freshness(tmp_path):
    store = SqliteMandiStore(tmp_path / "m.sqlite3")
    try:
        stale = await decisions.analysis(store, "tomato", "Guntur")
        assert stale["freshness"]["stale"] is True and stale["freshness"]["last_price_pull_at"] is None
        report = _new_report("datagov")
        report["status"] = "ok"
        await _finish(store, report)
        fresh = await decisions.analysis(store, "tomato", "Guntur")
        assert fresh["freshness"]["stale"] is False and fresh["freshness"]["hours_since_pull"] < 1
        assert fresh["action"]["confidence"] == "insufficient"
    finally:
        store.close()
