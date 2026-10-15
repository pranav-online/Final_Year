"""Phase 0 acceptance checks for the broker Demand Analysis redesign."""
import os

import pytest
from fastapi.testclient import TestClient

from config.security import create_access_token
from main import app
from services import demand_ml_service, market_service
from services.demand_analysis import REGION_COORDINATES, haversine_km
from services.market_service import get_all_market_alerts
from services.mandi.store import SqliteMandiStore, set_store
from services.region_service import REGIONS, get_distance_between


def _token(role: str) -> str:
    return create_access_token({"sub": f"test-{role}", "email": f"{role}@example.com", "role": role})


def _auth(role: str) -> dict:
    return {"Authorization": f"Bearer {_token(role)}"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    async def fake_alerts():
        return {"success": True, "alerts": [], "is_demo": False}

    monkeypatch.setattr("routes.notifications.get_all_market_alerts", fake_alerts)
    store = SqliteMandiStore(tmp_path / "mandi.sqlite3")  # never touch real data or wait on MongoDB
    set_store(store)
    yield TestClient(app)
    set_store(None)
    store.close()


# ─── Backend role enforcement ──────────────────────────────

def test_demand_endpoint_allows_broker(client):
    res = client.get("/market/demand/model", headers=_auth("broker"))
    assert res.status_code == 200


def test_demand_endpoint_rejects_farmer_with_403(client):
    res = client.get("/market/demand/model", headers=_auth("farmer"))
    assert res.status_code == 403


def test_demand_endpoint_rejects_missing_token_with_401(client):
    assert client.get("/market/demand/model").status_code == 401


def test_demand_endpoint_rejects_invalid_token_with_401(client):
    res = client.get("/market/demand/model", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


@pytest.mark.parametrize("path", [
    "/market/listings",
    "/market/supply",
    "/market/summary",
    "/market/thresholds",
    "/market/regions/all",
    "/notifications/alerts",
])
def test_broker_endpoints_require_broker_role(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers=_auth("farmer")).status_code == 403


def test_add_listing_requires_login(client):
    body = {"farmer_name": "A", "location": "Guntur", "crop_name": "Tomato",
            "quantity_kg": 10, "price_per_kg": 20}
    assert client.post("/market/listing/add", json=body).status_code == 401


# ─── No silent demo substitution ───────────────────────────


@pytest.mark.asyncio
async def test_empty_market_is_labelled_demo_and_not_persisted(monkeypatch):
    saved = []

    async def empty_index(query=None):
        return {}

    async def record_alert_history(signals):
        saved.extend(signals)

    monkeypatch.setattr(market_service, "_load_regional_supply_index", empty_index)
    monkeypatch.setattr(market_service, "_save_alert_history", record_alert_history)

    alerts = await get_all_market_alerts()

    assert alerts["is_demo"] is True and alerts["source"] == "demo_estimate"
    assert saved == []


# ─── One region table ──────────────────────────────────────

def test_every_region_has_coordinates_and_state():
    for name, data in REGIONS.items():
        assert isinstance(data["lat"], float) and isinstance(data["lng"], float), name
        assert data["state"], name


def test_demand_coordinates_come_from_region_service():
    assert set(REGION_COORDINATES) == {name.lower() for name in REGIONS}


def test_guntur_and_delhi_are_resolvable():
    assert get_distance_between("guntur", "hyderabad") > 0
    assert haversine_km("guntur", "hyderabad") is not None
    assert haversine_km("delhi", "jaipur") is not None


# ─── The synthetic 56-row regressor is gone (phase 3) ──────

def test_legacy_threshold_is_labelled_placeholder_not_ml():
    result = demand_ml_service.predict_dynamic_threshold(crop="tomato")
    assert result["threshold_type"] == "configured-static"
    assert "placeholder" in result["model"].lower()
    assert not hasattr(demand_ml_service, "X_TRAIN")
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert not os.path.exists(os.path.join(backend, "data", "demand_model.pkl"))
