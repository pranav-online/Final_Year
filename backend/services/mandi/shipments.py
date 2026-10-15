"""
Shipment lifecycle (master report section 2.10):

    initiated -> in_transit -> delivered
    initiated -> cancelled,  in_transit -> cancelled
    delivered / cancelled are final (records kept for audit).

Freight cost and ROI are always computed server-side from the report's truck
table; the client never supplies a cost.
"""
import uuid
from datetime import datetime, timezone

from services.mandi import freight
from services.mandi.config import resolve_commodity
from services.mandi.decisions import DecisionError, resolve_place, road_km, settings_with_defaults

TRANSITIONS = {
    "initiated": {"in_transit", "cancelled"},
    "in_transit": {"delivered", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}
# What happens to a linked farmer listing on each shipment status.
LISTING_STATUS = {"initiated": "pending", "delivered": "sold", "cancelled": "available"}


class ShipmentError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def initiate(store, broker_id: str, payload: dict, settings: dict = None, set_listing_status=None) -> dict:
    settings = settings_with_defaults(settings)
    cid = resolve_commodity(payload.get("crop"))
    if cid is None:
        raise ShipmentError(422, f"Unknown crop '{payload.get('crop')}'")
    try:
        source = resolve_place(payload.get("source_region"))
        destination = resolve_place(payload.get("destination_region"))
    except DecisionError as exc:
        raise ShipmentError(422, str(exc)) from None
    if source["city"] == destination["city"]:
        raise ShipmentError(422, "Source and destination must differ")
    quantity = float(payload.get("quantity_kg") or 0)
    if quantity <= 0:
        raise ShipmentError(422, "quantity_kg must be positive")
    truck = payload.get("truck_type") or settings["truck_type"]
    if truck and truck not in freight.TRUCKS:
        raise ShipmentError(422, f"truck_type must be one of {', '.join(freight.TRUCKS)}")

    distance = road_km(source, destination, settings["road_factor"])
    transport = freight.plan_transport(distance, quantity, truck, settings["truck_rates"])
    agreed, cost_price = payload.get("agreed_price_per_kg"), payload.get("source_price_per_kg")
    value = (freight.roi(agreed, cost_price, quantity, transport["cost"], settings["commission_pct"])
             if agreed is not None and cost_price is not None else None)

    now = _now()
    doc = {
        "_id": uuid.uuid4().hex,
        "broker_id": broker_id,
        "listing_id": payload.get("listing_id"),
        "commodity": cid,
        "source_region": source["city"],
        "destination_region": destination["city"],
        "destination_key": destination["city"].lower(),
        "quantity_kg": quantity,
        "distance_km": distance,
        "truck_type": transport["truck_type"],
        "trucks": transport["trucks"],
        "transport_cost": transport["cost"],
        "agreed_price_per_kg": agreed,
        "source_price_per_kg": cost_price,
        "roi": value,
        "roi_band": freight.roi_band(value),
        "status": "initiated",
        "history": [{"status": "initiated", "at": now}],
        "created_at": now,
        "dispatched_at": None,
    }
    await store.insert_shipment(doc)
    if doc["listing_id"] and set_listing_status:
        await set_listing_status(doc["listing_id"], LISTING_STATUS["initiated"])
    return doc


async def transition(store, broker_id: str, shipment_id: str, new_status: str, set_listing_status=None) -> dict:
    if new_status not in TRANSITIONS:
        raise ShipmentError(422, f"status must be one of {', '.join(TRANSITIONS)}")
    doc = await store.get_shipment(shipment_id)
    if not doc or doc["broker_id"] != broker_id:  # never reveal other brokers' shipments
        raise ShipmentError(404, "Shipment not found")
    if new_status not in TRANSITIONS[doc["status"]]:
        raise ShipmentError(409, f"Cannot move a shipment from '{doc['status']}' to '{new_status}'")

    now = _now()
    doc["status"] = new_status
    doc["history"].append({"status": new_status, "at": now})
    if new_status == "in_transit":
        doc["dispatched_at"] = now
    await store.update_shipment(shipment_id, doc)
    if doc.get("listing_id") and set_listing_status and new_status in LISTING_STATUS:
        await set_listing_status(doc["listing_id"], LISTING_STATUS[new_status])
    return doc
