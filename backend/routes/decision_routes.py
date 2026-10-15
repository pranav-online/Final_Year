"""Phase 4 broker decision endpoints: settings, best markets, analysis, matches, shipments."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from config.auth_deps import require_role
from services import market_service
from services.mandi import decisions, shipments
from services.mandi.config import COMMODITIES, resolve_commodity
from services.mandi.freight import TRUCKS
from services.mandi.store import get_store

router = APIRouter(prefix="/market/demand", tags=["Broker Decisions"])
broker = require_role("broker")

TruckType = Literal["small", "medium", "large"]


class BrokerSettings(BaseModel):
    home_region: Optional[str] = Field(None, description="City or state the broker trades from")
    watch_commodities: list[str] = Field(default_factory=list, description="Empty = all commodities")
    radius_km: float = Field(300, gt=0, le=1000)
    truck_type: Optional[TruckType] = None
    truck_rates: dict[TruckType, float] = Field(default_factory=dict, description="Rs/km overrides")
    commission_pct: float = Field(0.0, ge=0, le=20)
    road_factor: float = Field(1.25, ge=1.0, le=2.0)


class ShipmentRequest(BaseModel):
    crop: str
    source_region: str
    destination_region: str
    quantity_kg: float = Field(gt=0)
    truck_type: Optional[TruckType] = None
    listing_id: Optional[str] = None
    agreed_price_per_kg: Optional[float] = Field(None, gt=0)
    source_price_per_kg: Optional[float] = Field(None, gt=0)


class StatusChange(BaseModel):
    status: Literal["in_transit", "delivered", "cancelled"]


def _commodity(name: str) -> str:
    cid = resolve_commodity(name)
    if cid is None:
        raise HTTPException(status_code=404, detail=f"Unknown commodity '{name}'. Supported: {', '.join(COMMODITIES)}")
    return cid


async def _settings(user: dict) -> dict:
    stored = await (await get_store()).get_broker_settings(user["sub"])
    return decisions.settings_with_defaults({**(stored or {}), "broker_id": user["sub"]})


@router.get("/settings")
async def get_settings(user: dict = Depends(broker)):
    return {"success": True, "settings": await _settings(user), "trucks": TRUCKS}


@router.put("/settings")
async def put_settings(body: BrokerSettings, user: dict = Depends(broker)):
    if body.home_region:
        try:
            decisions.resolve_place(body.home_region)
        except decisions.DecisionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
    unknown = [c for c in body.watch_commodities if resolve_commodity(c) is None]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown commodities: {', '.join(unknown)}")
    doc = {**body.model_dump(), "watch_commodities": [resolve_commodity(c) for c in body.watch_commodities],
           "broker_id": user["sub"]}
    await (await get_store()).put_broker_settings(user["sub"], doc)
    return {"success": True, "settings": decisions.settings_with_defaults(doc)}


@router.get("/best-markets")
async def best_markets(
    commodity: str, source: str, qty_kg: float = Query(gt=0),
    source_price_per_kg: float = Query(None, gt=0), truck: TruckType = None,
    sort: Literal["net", "composite"] = "net", limit: int = Query(5, ge=1, le=20),
    user: dict = Depends(broker),
):
    settings = await _settings(user)
    if truck:
        settings["truck_type"] = truck
    try:
        result = await decisions.best_markets(await get_store(), _commodity(commodity), source, qty_kg,
                                              source_price_per_kg, settings, limit, sort)
    except decisions.DecisionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return {"success": True, "is_demo": False, **result}


@router.get("/analysis/{commodity}")
async def full_analysis(
    commodity: str, location: str, qty_kg: float = Query(None, gt=0),
    price_per_kg: float = Query(None, gt=0), user: dict = Depends(broker),
):
    try:
        result = await decisions.analysis(
            await get_store(), _commodity(commodity), location, qty_kg, price_per_kg,
            await _settings(user), await market_service.load_listings({"status": "available"}))
    except decisions.DecisionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return {"success": True, **result}


@router.get("/matches")
async def matches(commodity: str = None, user: dict = Depends(broker)):
    settings = await _settings(user)
    if not settings["home_region"]:
        raise HTTPException(status_code=422, detail="Set your home region first (PUT /market/demand/settings)")
    found = await decisions.matches_for_broker(
        await get_store(), settings, await market_service.load_listings({"status": "available"}),
        _commodity(commodity) if commodity else None)
    return {"success": True, "total": len(found), "matches": found}


@router.post("/initiate-shipment", status_code=201)
async def initiate_shipment(body: ShipmentRequest, user: dict = Depends(broker)):
    if body.listing_id:
        listing = await market_service.get_listing(body.listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing.get("status") != "available":
            raise HTTPException(status_code=409, detail=f"Listing is already {listing.get('status')}")
    try:
        doc = await shipments.initiate(await get_store(), user["sub"], body.model_dump(),
                                       await _settings(user), market_service.set_listing_status)
    except shipments.ShipmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return {"success": True, "shipment": _public(doc)}


@router.get("/shipments")
async def list_shipments(status: str = None, user: dict = Depends(broker)):
    docs = await (await get_store()).find_shipments(broker_id=user["sub"], status=status)
    return {"success": True, "total": len(docs), "shipments": [_public(d) for d in docs]}


@router.post("/shipments/{shipment_id}/status")
async def change_status(shipment_id: str, body: StatusChange, user: dict = Depends(broker)):
    try:
        doc = await shipments.transition(await get_store(), user["sub"], shipment_id, body.status,
                                         market_service.set_listing_status)
    except shipments.ShipmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return {"success": True, "shipment": _public(doc)}


def _public(doc: dict) -> dict:
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    return out
