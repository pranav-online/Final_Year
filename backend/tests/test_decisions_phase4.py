"""Phase 4 acceptance checks: broker decisions, matching and shipments."""
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from config.security import create_access_token
from models.market import CropListing, CropStatus
from services import market_service
from services.mandi import decisions, freight
from services.mandi.store import SqliteMandiStore, set_store
from services.region_service import REGIONS, haversine_distance


def guntur_hyderabad_road_km():
    g, h = REGIONS["Guntur"], REGIONS["Hyderabad"]
    return round(haversine_distance(g["lat"], g["lng"], h["lat"], h["lng"]) * 1.25, 1)


def state_signal(commodity, state, price_per_quintal, quadrant="balanced", urgency=None):
    key = state.lower()
    return {"_id": f"{commodity}|state|{key}", "commodity": commodity, "level": "state", "scope_key": key,
            "scope_name": state, "state": state, "price": price_per_quintal, "week_start": "2026-10-12",
            "quadrant": quadrant, "urgency": urgency, "stale": False}


@pytest.fixture
def store(tmp_path):
    s = SqliteMandiStore(tmp_path / "mandi.sqlite3")
    yield s
    s.close()


# ─── Freight and ROI (report section 2.6) ──────────────────

def test_report_worked_example_roi():
    # Guntur tomato bought at Rs 22/kg, 2,500 kg, Hyderabad 280 km, medium truck (Rs 35/km).
    # ROI 2.1 means margin = 2.1 x 280 x 35 = 20,580 -> agreed price 22 + 20,580 / 2,500 = 30.232.
    plan = freight.plan_transport(280, 2500, "medium")
    assert plan["cost"] == 9800 and plan["trucks"] == 1
    assert freight.roi(30.232, 22, 2500, plan["cost"]) == 2.1
    assert freight.roi_band(2.1) == "Good"
    assert freight.roi_band(1.2) == "Acceptable" and freight.roi_band(0.99) == "Loss-Making"


def test_cheapest_truck_and_multi_truck_loads():
    assert freight.plan_transport(280, 2500)["truck_type"] == "small"         # 1 x 25/km
    big = freight.plan_transport(100, 25000)                                    # small 9x25, medium 3x35, large 2x50
    assert big["truck_type"] == "large" and big["trucks"] == 2 and big["cost"] == 10000
    assert freight.plan_transport(100, 2500, rates={"small": 60})["truck_type"] == "medium"  # broker override


def test_transport_efficiency_formula():
    assert freight.transport_efficiency_score(280) == 44.0   # 100 - 280/5
    assert freight.transport_efficiency_score(900) == 0.0


def test_commission_reduces_roi():
    assert freight.roi(30, 22, 1000, 4000, commission_pct=2) == pytest.approx((8000 - 600) / 4000)


# ─── Best markets ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_best_markets_arithmetic_to_the_rupee(store):
    await store.replace_signals("tomato", [
        state_signal("tomato", "Telangana", 3000, quadrant="supply_shortage"),
        state_signal("tomato", "Tamil Nadu", 2800),
    ])
    result = await decisions.best_markets(store, "tomato", "Guntur", 2500, source_price_per_kg=22)

    hyd = next(d for d in result["destinations"] if d["destination"] == "Hyderabad")
    km = guntur_hyderabad_road_km()
    cost = round(km * 25, 2)                       # small truck is cheapest for 2.5 t
    assert hyd["distance_km"] == km
    assert hyd["transport"]["truck_type"] == "small" and hyd["transport"]["cost"] == cost
    assert hyd["net_price_per_kg"] == round(30 - cost / 2500, 2)
    assert hyd["expected_margin"] == round((30 - cost / 2500 - 22) * 2500, 2)
    assert hyd["roi"] == round((30 - 22) * 2500 / cost, 2) and hyd["roi_band"] == "Good"
    assert hyd["uses_forecast"] is False and hyd["downside_price_per_kg"] is None
    assert hyd["markets_in_sample"] == 1 and hyd["thin_sample"] is True  # one state median, unknown markets

    # Ranked by expected margin; Andhra cities have no price data and are reported, not invented.
    margins = [d["expected_margin"] for d in result["destinations"]]
    assert margins == sorted(margins, reverse=True)
    assert any(s["city"] == "Vijayawada" for s in result["skipped_no_price"])
    assert all(d["distance_km"] <= freight.MAX_HAUL_KM for d in result["destinations"])

    comp = hyd["composite"]
    assert comp["factors"]["demand_gap"] == 100          # destination in supply shortage
    assert comp["factors"]["reliability"] is None and comp["active_weight"] == 0.6
    assert set(result["inactive_factors"]) == {"reliability", "storage", "weather"}


@pytest.mark.asyncio
async def test_best_markets_uses_forecast_and_p10_downside(store):
    await store.replace_signals("tomato", [state_signal("tomato", "Telangana", 3000)])
    await store.replace_scoped("forecasts", "tomato", [{
        "_id": "tomato|state|telangana", "commodity": "tomato", "level": "state", "scope_key": "telangana",
        "confidence": "high", "horizons": [
            {"h_weeks": 1, "target_week": "2026-10-19", "p10": 2600, "p50": 3200, "p90": 3700},
            {"h_weeks": 2, "target_week": "2026-10-26", "p10": 2500, "p50": 3100, "p90": 3700},
            {"h_weeks": 4, "target_week": "2026-11-09", "p10": 2400, "p50": 3000, "p90": 3800}]}])
    hyd = (await decisions.best_markets(store, "tomato", "Guntur", 2500, 22))["destinations"][0]
    assert hyd["uses_forecast"] and hyd["expected_price_per_kg"] == 32.0 and hyd["downside_price_per_kg"] == 26.0
    assert hyd["roi_p10"] < hyd["roi"]


@pytest.mark.asyncio
async def test_best_markets_without_any_price_is_an_error(store):
    with pytest.raises(decisions.DecisionError):
        await decisions.best_markets(store, "tomato", "Guntur", 2500)  # no source price, none given
    with pytest.raises(decisions.DecisionError):
        await decisions.best_markets(store, "tomato", "Atlantis", 2500, 22)


def test_break_even_week():
    source = [{"h_weeks": 1, "p50": 2200}, {"h_weeks": 2, "p50": 2300}, {"h_weeks": 4, "p50": 2400}]
    dest = [{"h_weeks": 1, "p50": 2600, "target_week": "w1"}, {"h_weeks": 2, "p50": 2500, "target_week": "w2"},
            {"h_weeks": 4, "p50": 2400, "target_week": "w4"}]
    # Freight Rs 2.5/kg: week 1 26-2.5=23.5 > 22; week 2 25-2.5=22.5 < 23 -> break-even week 2.
    assert decisions.break_even(source, dest, 2.5)["week"] == 2
    # Rs 0.1/kg: weeks 1-2 stay ahead; week 4 gives 24 - 0.1 = 23.9 < 24 -> week 4.
    assert decisions.break_even(source, dest, 0.1)["week"] == 4
    assert decisions.break_even(source, dest, 0.0)["week"] is None  # never strictly below
    assert decisions.break_even([], dest, 2.5)["week"] is None


# ─── API: matching and shipments ───────────────────────────

class OfflineMarket:
    """MongoDB unavailable: market_service falls back to the in-memory store below."""

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise PyMongoError("offline")
        return fail


@pytest.fixture
def api(store, monkeypatch):
    listings = []

    async def insert_listing(doc):
        listing_id = uuid.uuid4().hex
        listings.append({**doc, "_id": listing_id, "created_at": doc["created_at"].isoformat()})
        return listing_id

    async def find_listings(query=None):
        return [dict(l) for l in listings if all(l.get(k) == v for k, v in (query or {}).items())]

    async def update_listing(listing_id, fields):
        for l in listings:
            if l["_id"] == listing_id:
                l.update(fields)
                return True
        return False

    monkeypatch.setattr(market_service, "market_collection", OfflineMarket())
    monkeypatch.setattr(market_service.local_market_store, "insert_listing", insert_listing)
    monkeypatch.setattr(market_service.local_market_store, "find_listings", find_listings)
    monkeypatch.setattr(market_service.local_market_store, "update_listing", update_listing)
    set_store(store)
    from main import app
    yield TestClient(app), listings
    set_store(None)


def auth(role, sub=None):
    return {"Authorization": f"Bearer {create_access_token({'sub': sub or role, 'role': role})}"}


def test_new_listing_alerts_a_matching_broker_within_5_seconds(api):
    client, _ = api
    near = auth("broker", "broker-hyd")
    other = auth("broker", "broker-wheat")
    assert client.put("/market/demand/settings", headers=near, json={
        "home_region": "Hyderabad", "watch_commodities": ["tomato"], "radius_km": 300}).status_code == 200
    client.put("/market/demand/settings", headers=other, json={
        "home_region": "Hyderabad", "watch_commodities": ["wheat"], "radius_km": 300})

    started = time.monotonic()
    res = client.post("/market/listing/add", headers=auth("farmer", "farmer-1"), json={
        "farmer_name": "Asha", "location": "Guntur", "crop_name": "Tomato",
        "quantity_kg": 2500, "price_per_kg": 22})
    assert res.status_code == 200 and "listing" not in res.json()

    alerts = client.get("/market/demand/alerts", headers=near).json()["alerts"]
    assert time.monotonic() - started < 5
    match = next(a for a in alerts if a["type"] == "listing_match")
    assert match["listing_id"] == res.json()["id"] and match["broker_id"] == "broker-hyd"
    # A broker watching another crop, and other brokers in general, see nothing.
    assert not [a for a in client.get("/market/demand/alerts", headers=other).json()["alerts"]
                if a["type"] == "listing_match"]

    ranked = client.get("/market/demand/matches", headers=near).json()
    assert ranked["total"] == 1 and ranked["matches"][0]["distance_km"] == guntur_hyderabad_road_km()


def test_listing_records_farmer_and_commodity(api):
    client, listings = api
    client.post("/market/listing/add", headers=auth("farmer", "farmer-7"), json={
        "farmer_name": "Ravi", "location": "Nashik", "crop_name": "Pyaz",
        "quantity_kg": 800, "price_per_kg": 18, "available_from": "2026-10-20"})
    assert listings[-1]["farmer_id"] == "farmer-7"
    assert listings[-1]["commodity_id"] == "onion" and listings[-1]["available_from"] == "2026-10-20"


def test_shipment_lifecycle(api):
    client, listings = api
    broker = auth("broker", "b1")
    listing_id = client.post("/market/listing/add", headers=auth("farmer"), json={
        "farmer_name": "Asha", "location": "Guntur", "crop_name": "Tomato",
        "quantity_kg": 2500, "price_per_kg": 22}).json()["id"]

    created = client.post("/market/demand/initiate-shipment", headers=broker, json={
        "crop": "tomato", "source_region": "Guntur", "destination_region": "Hyderabad",
        "quantity_kg": 2500, "truck_type": "medium", "listing_id": listing_id,
        "agreed_price_per_kg": 30.232, "source_price_per_kg": 22})
    assert created.status_code == 201
    ship = created.json()["shipment"]
    km = guntur_hyderabad_road_km()
    assert ship["status"] == "initiated" and ship["transport_cost"] == round(km * 35, 2)
    assert ship["roi"] == round((30.232 - 22) * 2500 / (km * 35), 2)
    assert next(l for l in listings if l["_id"] == listing_id)["status"] == "pending"

    # The same listing cannot be shipped twice.
    again = client.post("/market/demand/initiate-shipment", headers=broker, json={
        "crop": "tomato", "source_region": "Guntur", "destination_region": "Chennai",
        "quantity_kg": 2500, "listing_id": listing_id})
    assert again.status_code == 409

    url = f"/market/demand/shipments/{ship['id']}/status"
    assert client.post(url, headers=auth("broker", "someone-else"), json={"status": "in_transit"}).status_code == 404
    assert client.post(url, headers=auth("farmer"), json={"status": "in_transit"}).status_code == 403
    assert client.post(url, headers=broker, json={"status": "delivered"}).status_code == 409  # must dispatch first
    moving = client.post(url, headers=broker, json={"status": "in_transit"}).json()["shipment"]
    assert moving["dispatched_at"]
    done = client.post(url, headers=broker, json={"status": "delivered"}).json()["shipment"]
    assert [h["status"] for h in done["history"]] == ["initiated", "in_transit", "delivered"]
    assert next(l for l in listings if l["_id"] == listing_id)["status"] == "sold"
    for illegal in ("in_transit", "cancelled"):
        assert client.post(url, headers=broker, json={"status": illegal}).status_code == 409

    mine = client.get("/market/demand/shipments", headers=broker).json()
    assert mine["total"] == 1 and client.get("/market/demand/shipments", headers=auth("broker", "x")).json()["total"] == 0


def test_cancelled_shipment_releases_the_listing(api):
    client, listings = api
    broker = auth("broker", "b2")
    listing_id = client.post("/market/listing/add", headers=auth("farmer"), json={
        "farmer_name": "A", "location": "Guntur", "crop_name": "Onion",
        "quantity_kg": 1000, "price_per_kg": 15}).json()["id"]
    ship = client.post("/market/demand/initiate-shipment", headers=broker, json={
        "crop": "onion", "source_region": "Guntur", "destination_region": "Chennai",
        "quantity_kg": 1000, "listing_id": listing_id}).json()["shipment"]
    client.post(f"/market/demand/shipments/{ship['id']}/status", headers=broker, json={"status": "cancelled"})
    assert next(l for l in listings if l["_id"] == listing_id)["status"] == "available"


def test_settings_validation(api):
    client, _ = api
    broker = auth("broker", "b3")
    assert client.put("/market/demand/settings", headers=broker, json={"home_region": "Atlantis"}).status_code == 422
    assert client.put("/market/demand/settings", headers=broker,
                      json={"watch_commodities": ["kiwi"]}).status_code == 422
    assert client.get("/market/demand/matches", headers=broker).status_code == 422  # no home region yet
    assert client.get("/market/demand/settings", headers=auth("farmer")).status_code == 403


def test_analysis_endpoint_is_not_captured_by_the_legacy_region_route(api, store):
    client, _ = api
    body = client.get("/market/demand/analysis/tomato?location=Guntur", headers=auth("broker")).json()
    assert body["success"] and body["commodity"] == "tomato" and body["state"] == "Andhra Pradesh"
    assert client.get("/market/demand/best-markets?commodity=tomato&source=Guntur&qty_kg=2500",
                      headers=auth("broker")).status_code == 422  # honest: no price data yet


def test_legacy_reserved_status_maps_to_pending():
    listing = CropListing(farmer_name="A", location="Guntur", crop_name="Tomato",
                          quantity_kg=1, price_per_kg=1, status="reserved")
    assert listing.status == CropStatus.pending
