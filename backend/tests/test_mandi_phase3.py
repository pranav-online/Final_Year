"""Phase 3 acceptance checks: forecasting with an honest promotion gate."""
import math
from datetime import date, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from config.security import create_access_token
from services.mandi import forecast as fc
from services.mandi.normalize import build_price_row
from services.mandi.store import SqliteMandiStore, set_store

START = date(2022, 1, 3)  # a Monday
WEEKS = 160


def structured_prices(rng, offset=0.0, weeks=WEEKS, phi=0.8, sigma=0.06):
    """Seasonal level plus a mean-reverting AR(1) shock: predictable beyond both naive baselines."""
    x, out = 0.0, []
    for t in range(weeks):
        x = phi * x + rng.normal(0, sigma)
        season = 0.25 * math.cos(2 * math.pi * (t - 43) / 52)
        out.append(2000 * math.exp(offset + season + x))
    return np.array(out)


def random_walk_prices(rng, weeks=WEEKS, sigma=0.06):
    return 2000 * np.exp(np.cumsum(rng.normal(0, sigma, weeks)))


def panel_of(price_arrays, commodity="onion"):
    national = fc.Series(commodity, "national", "india", "India", START, np.median(price_arrays, axis=0))
    return [national] + [
        fc.Series(commodity, "market", f"s|d|m{i}", f"M{i}", START, prices, parent=national)
        for i, prices in enumerate(price_arrays)
    ]


@pytest.fixture(scope="module")
def structured_backtest():
    rng = np.random.default_rng(7)
    panel = panel_of([structured_prices(rng, offset=0.1 * i) for i in range(8)])
    return fc.backtest(panel, return_rows=True)


# ─── Features and leakage ──────────────────────────────────

def test_features_do_not_look_ahead():
    rng = np.random.default_rng(1)
    s = panel_of([structured_prices(rng)])[1]
    t = 100
    before = fc.features_at(s, t, 2)
    s.prices[t + 1:] = s.prices[t + 1:] * 5  # rewrite the future
    assert fc.features_at(s, t, 2) == before


def test_backtest_predictions_ignore_later_data(structured_backtest):
    rng = np.random.default_rng(7)
    arrays = [structured_prices(rng, offset=0.1 * i) for i in range(8)]
    cutoff = START + timedelta(weeks=130)
    changed = [a.copy() for a in arrays]
    for a in changed:
        a[131:] *= 3  # everything after the cutoff week is different
    rows = fc.backtest(panel_of(changed), return_rows=True)["rows"]
    original = structured_backtest["rows"]
    for h in fc.HORIZONS:
        early = lambda rs: sorted((r["series"], r["origin_week"], round(r["p50"], 6))
                                  for r in rs if r["origin_week"] <= (cutoff - timedelta(weeks=h)).isoformat())
        assert early(rows[h]) and early(rows[h]) == early(original[h])


# ─── Gate ──────────────────────────────────────────────────

def test_conformal_correction_is_learnt_from_past_scores_only():
    assert fc.conformal_widen([0.1] * 5) == 0.0  # too few scores: no correction yet
    scores = np.linspace(-0.2, 0.2, 100)
    assert fc.conformal_widen(scores) == pytest.approx(np.quantile(scores, 81 / 100))


def test_structured_panel_beats_baselines_and_is_promoted(structured_backtest):
    h1 = structured_backtest["by_horizon"]["h1"]
    assert h1["share_beating_baseline"] >= 0.6
    assert 0.70 <= h1["coverage_80"] <= 0.90
    assert h1["directional_accuracy"] > 0.55
    gate = fc.evaluate_gate(structured_backtest)
    assert gate["promoted"] is True, gate["reasons"]


def test_random_walk_panel_is_refused():
    rng = np.random.default_rng(11)
    report = fc.backtest(panel_of([random_walk_prices(rng) for _ in range(8)]))
    gate = fc.evaluate_gate(report)
    assert gate["promoted"] is False
    assert gate["reasons"]


def test_rel_mae_is_against_the_strongest_baseline():
    rows = [{"actual": 100.0, "p50": 104.0, "p10": 90.0, "p90": 110.0, "origin_price": 101.0,
             "naive": 101.0, "seasonal_naive": 150.0, "moving_avg_4": 120.0} for _ in range(5)]
    m = fc._metrics(rows)
    assert m["baseline"] == "naive"          # the hardest one to beat here
    assert m["rel_mae"] == pytest.approx(4.0)  # 4 / 1, not 4 / 50 against seasonal naive


def test_quantiles_are_always_ordered():
    class Crossing:  # a model whose quantiles cross: P90 below P10
        def __init__(self, v):
            self.v = v

        def predict(self, X):
            return np.full(len(X), self.v)

    models = {0.1: Crossing(0.2), 0.5: Crossing(0.0), 0.9: Crossing(-0.2)}
    out = fc.predict_prices(models, np.zeros((3, len(fc.FEATURES))), np.array([100.0, 200.0, 300.0]))
    assert (out[:, 0] <= out[:, 1]).all() and (out[:, 1] <= out[:, 2]).all()


def test_confidence_rules():
    good = {"h1": {"rel_mae": 0.7, "coverage_80": 0.8, "baseline": "naive"}}
    assert fc._confidence(good, 100, False) == ("high", None)
    assert fc._confidence({"h1": {**good["h1"], "rel_mae": 0.95}}, 100, False)[0] == "medium"
    assert fc._confidence({"h1": {**good["h1"], "rel_mae": 1.1}}, 100, False)[0] == "insufficient"
    assert fc._confidence(good, 10, False)[0] == "insufficient"
    assert fc._confidence(good, 100, True)[0] == "insufficient"
    assert fc._confidence(None, 100, False)[0] == "insufficient"


# ─── Training, serving and API ─────────────────────────────

async def seed_structured_store(store, seed=3):
    rng = np.random.default_rng(seed)
    rows = []
    for m, (state, district) in enumerate([("Maharashtra", "Nashik")] * 3 + [("Karnataka", "Kolar")] * 3):
        prices = structured_prices(rng, offset=0.05 * m)
        for t, price in enumerate(prices):
            row, _ = build_price_row(
                date=(START + timedelta(weeks=t)).isoformat(), state=state, district=district,
                market=f"Mandi {m}", commodity_raw="Onion", variety="Red", grade="FAQ",
                min_price=price * 0.9, max_price=price * 1.1, modal_price=price, source="datagov", raw={})
            rows.append(row)
    # a young market: too little history for any forecast
    for t in range(10):
        row, _ = build_price_row(
            date=(START + timedelta(weeks=WEEKS - 10 + t)).isoformat(), state="Karnataka", district="Kolar",
            market="New Mandi", commodity_raw="Onion", variety="Red", grade="FAQ",
            min_price=1800, max_price=2200, modal_price=2000, source="datagov", raw={})
        rows.append(row)
    await store.upsert_prices(rows)
    return START + timedelta(weeks=WEEKS - 1)


@pytest.mark.asyncio
async def test_train_promote_forecast_and_serve(tmp_path, monkeypatch):
    # Plumbing test: storage -> panel -> train -> save -> serve -> API. Model skill and
    # the gate itself are covered by the structured / random-walk tests above, so the
    # gate is forced open here rather than tuning this small fixture until it passes.
    real_gate = fc.evaluate_gate
    monkeypatch.setattr(fc, "evaluate_gate", lambda report: {**real_gate(report), "promoted": True, "reasons": []})
    store = SqliteMandiStore(tmp_path / "mandi.sqlite3")
    try:
        today = await seed_structured_store(store)
        result = await fc.train_and_evaluate(store, ["onion"], today=today, model_root=tmp_path / "models")
        assert result["trained"] and result["promoted"]
        assert set(result["backtest"]["conformal_widen"]) == {"h1", "h2", "h4"}
        assert (tmp_path / "models" / result["version"] / "meta.json").exists()

        summary = await fc.run_forecasts(store, ["onion"], today=today, model_root=tmp_path / "models")
        assert summary["model_version"] == result["version"]
        docs = {d["scope_key"]: d for d in await store.find_scoped("forecasts", "onion")}
        young = next(d for k, d in docs.items() if k.endswith("new mandi"))
        assert young["confidence"] == "insufficient" and young["horizons"] == []
        served = [d for d in docs.values() if d["confidence"] != "insufficient"]
        assert served
        for d in served:
            assert [h["h_weeks"] for h in d["horizons"]] == [1, 2, 4]
            assert all(h["p10"] <= h["p50"] <= h["p90"] for h in d["horizons"])

        from main import app
        set_store(store)
        client = TestClient(app)
        broker = {"Authorization": f"Bearer {create_access_token({'sub': 'b', 'role': 'broker'})}"}
        body = client.get("/market/demand/forecast/pyaz", headers=broker).json()
        assert body["success"] and body["scope_key"] == "india" and body["model_version"] == result["version"]
        assert client.get("/market/demand/forecast/onion?level=state", headers=broker).status_code == 422
        assert client.get("/market/demand/forecast/onion?level=state&scope=Goa", headers=broker).status_code == 404
        model = client.get("/market/demand/model", headers=broker).json()
        assert model["in_use"]["_id"] == result["version"] and model["latest_run"]["promoted"] is True
        assert client.get("/market/demand/model").status_code == 401
    finally:
        set_store(None)
        store.close()


@pytest.mark.asyncio
async def test_failed_gate_saves_version_but_does_not_promote(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "evaluate_gate", lambda report: {"promoted": False, "reasons": ["test: refused"]})
    store = SqliteMandiStore(tmp_path / "mandi.sqlite3")
    try:
        today = await seed_structured_store(store)
        result = await fc.train_and_evaluate(store, ["onion"], today=today, model_root=tmp_path / "models")
        assert result["trained"] is True and result["promoted"] is False
        assert await fc.promoted_version(store) is None
        registry = await store.get_master("model_registry")
        assert registry[-1]["gate_reasons"] == ["test: refused"]
    finally:
        store.close()


@pytest.mark.asyncio
async def test_without_a_promoted_model_every_series_says_not_enough_signal(tmp_path):
    store = SqliteMandiStore(tmp_path / "mandi.sqlite3")
    try:
        today = await seed_structured_store(store)
        summary = await fc.run_forecasts(store, ["onion"], today=today, model_root=tmp_path / "models")
        assert summary["model_version"] is None
        docs = await store.find_scoped("forecasts", "onion")
        assert docs and all(d["confidence"] == "insufficient" and not d["horizons"] for d in docs)
        assert all("gate" in d["reason"] for d in docs)
    finally:
        store.close()
