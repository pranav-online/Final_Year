import datetime

from config.database import market_alerts_collection, market_collection
from models.market import CropListing
from pymongo.errors import PyMongoError
from services.demand_analysis import (
    DEMAND_THRESHOLDS,
    add_supply,
    build_market_signal,
    empty_supply_index,
    get_demand_threshold,
    normalize_key,
)
from services.demand_ml_service import (
    predict_dynamic_threshold,
    estimate_price_impact,
)
from services.region_service import (
    get_all_regions,
    get_region_info,
)
from services import local_market_store
from services.mandi.config import resolve_commodity
from bson import ObjectId


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _listing_to_doc(listing: CropListing, farmer_id: str = None) -> dict:
    return {
        "farmer_name": listing.farmer_name,
        "farmer_id": farmer_id,
        "location": normalize_key(listing.location),
        "crop_name": normalize_key(listing.crop_name),
        # canonical commodity id for mandi matching (None for untracked crops)
        "commodity_id": resolve_commodity(listing.crop_name),
        "quantity_kg": listing.quantity_kg,
        "price_per_kg": listing.price_per_kg,
        "status": listing.status.value,
        "contact": listing.contact,
        "available_from": listing.available_from.isoformat() if listing.available_from else None,
        "created_at": datetime.datetime.utcnow(),
    }


def _mongo_id(listing_id: str):
    return ObjectId(listing_id) if ObjectId.is_valid(listing_id) else listing_id


async def set_listing_status(listing_id: str, status: str) -> bool:
    """Move a listing through available -> pending -> sold (driven by shipments)."""
    try:
        result = await market_collection.update_one({"_id": _mongo_id(listing_id)}, {"$set": {"status": status}})
        return result.matched_count > 0
    except PyMongoError:
        return await local_market_store.update_listing(listing_id, {"status": status})


async def get_listing(listing_id: str):
    try:
        doc = await market_collection.find_one({"_id": _mongo_id(listing_id)})
    except PyMongoError:
        docs = await local_market_store.find_listings({"_id": listing_id})
        doc = docs[0] if docs else None
    return doc


async def load_listings(query: dict = None) -> list[dict]:
    try:
        return [doc async for doc in market_collection.find(query or {})]
    except PyMongoError:
        return await local_market_store.find_listings(query)


def _build_supply_summary_from_listings(listings: list[dict]) -> dict:
    supply = {}
    for doc in listings:
        crop = doc["crop_name"]
        qty = doc["quantity_kg"]
        if crop not in supply:
            supply[crop] = {
                "total_quantity_kg": 0,
                "listings_count": 0,
                "avg_price_per_kg": 0,
                "prices": [],
            }
        supply[crop]["total_quantity_kg"] += qty
        supply[crop]["listings_count"] += 1
        supply[crop]["prices"].append(doc["price_per_kg"])

    for crop in supply:
        prices = supply[crop]["prices"]
        supply[crop]["avg_price_per_kg"] = round(sum(prices) / len(prices), 2)
        del supply[crop]["prices"]

    return supply


def _build_regional_supply_summary_from_listings(listings: list[dict]) -> dict:
    listings_by_region = {}
    for listing in listings:
        region = normalize_key(listing.get("location"))
        if region:
            listings_by_region.setdefault(region, []).append(listing)

    return {
        region: _build_supply_summary_from_listings(region_listings)
        for region, region_listings in listings_by_region.items()
    }


def _build_regional_data_from_listings(listings: list[dict]) -> dict:
    regional_data = empty_supply_index()
    for doc in listings:
        add_supply(
            regional_data,
            doc.get("location"),
            doc.get("crop_name"),
            doc.get("quantity_kg", 0),
        )
    return regional_data


def _seed_demo_regional_data() -> dict:
    demo = empty_supply_index()
    regional_samples = {
        "hyderabad": {"rice": 650, "maize": 420, "cotton": 220},
        "vijayawada": {"rice": 820, "maize": 350, "cotton": 280},
        "chennai": {"rice": 480, "groundnut": 310, "sugarcane": 700},
        "bangalore": {"maize": 380, "rice": 260, "tomato": 180},
        "pune": {"wheat": 520, "onion": 290, "maize": 360},
        "kochi": {"rice": 440, "tomato": 210, "coconut": 190},
        "lucknow": {"wheat": 710, "rice": 410, "onion": 240},
    }
    for region, crops in regional_samples.items():
        for crop, qty in crops.items():
            add_supply(demo, region, crop, qty)
    return demo


def _build_demo_supply_summary(region: str) -> dict:
    regional_supply = _seed_demo_regional_data().get(normalize_key(region), {})
    return {
        crop: {
            "total_quantity_kg": quantity,
            "listings_count": 0,
            "avg_price_per_kg": None,
        }
        for crop, quantity in regional_supply.items()
    }


async def _load_local_regional_supply_index(query: dict = None) -> dict:
    listings = await local_market_store.find_listings(query or {"status": "available"})
    return _build_regional_data_from_listings(listings)


async def _load_regional_supply_index(query: dict = None) -> dict:
    cursor = market_collection.find(query or {"status": "available"})
    regional_data = empty_supply_index()

    async for doc in cursor:
        add_supply(
            regional_data,
            doc.get("location"),
            doc.get("crop_name"),
            doc.get("quantity_kg", 0),
        )

    return regional_data


async def _load_supply_index_any_storage() -> tuple[dict, str]:
    """Load the regional supply index from MongoDB, falling back to the local store."""
    try:
        return await _load_regional_supply_index(), "mongodb"
    except PyMongoError:
        return await _load_local_regional_supply_index(), "local"


def _with_demo_fallback(regional_data: dict) -> tuple[dict, bool]:
    """
    Use the demo seed only when there are no farmer listings anywhere, and
    report that it was used so every response can label it (is_demo).
    """
    if regional_data:
        return regional_data, False
    return _seed_demo_regional_data(), True


async def _save_alert_history(signals: list) -> None:
    now = datetime.datetime.utcnow()
    for signal in signals:
        await market_alerts_collection.update_one(
            {"id": signal["id"]},
            {
                "$set": {
                    **signal,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": now,
                },
            },
            upsert=True,
        )


def _estimate_expected_demand(region: str, crop: str) -> dict:
    crop_key = normalize_key(crop)
    info = get_region_info(region) or {}
    try:
        prediction = predict_dynamic_threshold(
            crop=crop_key,
            region_type=info.get("region_type", "semi-urban"),
            population_density=info.get("population_density", 3000),
            market_size=info.get("market_size", "medium"),
        )
        return {
            "expected_demand_kg": prediction["predicted_threshold_kg"],
            "model": prediction["model"],
            "season": prediction["season"],
        }
    except Exception:
        return {
            "expected_demand_kg": get_demand_threshold(crop_key),
            "model": "Configured crop threshold fallback",
        }


def _build_demand_result(region: str, supply_summary: dict, regional_data: dict) -> dict:
    candidate_regions = set(get_all_regions()) | set(regional_data) | {region}
    demand_by_crop = {}
    alerts = []
    recommendations = []
    crop_analysis = {}
    signals = []

    for crop, total_qty in supply_summary.items():
        demand_estimates = {
            normalize_key(candidate): _estimate_expected_demand(candidate, crop)
            for candidate in candidate_regions
        }
        expected_demand_by_region = {
            key: estimate["expected_demand_kg"]
            for key, estimate in demand_estimates.items()
        }
        expected_demand = demand_estimates.get(
            normalize_key(region), _estimate_expected_demand(region, crop)
        )
        expected_demand_kg = expected_demand["expected_demand_kg"]
        signal = build_market_signal(
            region=region,
            crop=crop,
            quantity=total_qty,
            regional_data=regional_data,
            threshold=expected_demand_kg,
            expected_demand_by_region=expected_demand_by_region,
        )
        signals.append(signal)

        market_status = "balanced" if signal["type"] == "normal" else signal["type"]
        price_impact = (
            estimate_price_impact(crop, total_qty, expected_demand_kg)
            if market_status == "oversupply"
            else None
        )
        if market_status == "balanced":
            recommendation = "Supply is close to expected demand; no major redistribution is needed."
        elif signal["redistribution_options"]:
            recommendation = signal["action"]
        elif market_status == "oversupply":
            recommendation = (
                f"No undersupplied destination appears in available regional data. "
                f"Find alternate buyers for {crop.title()}."
            )
        else:
            recommendation = (
                f"No nearby oversupplied source appears in available listings. "
                f"Source additional {crop.title()} from outside the listed regions."
            )
        signal["action"] = recommendation
        crop_analysis[crop] = {
            "current_supply_kg": round(float(total_qty or 0), 2),
            "expected_demand_kg": expected_demand_kg,
            "supply_demand_ratio": signal["supply_demand_ratio"],
            "market_status": market_status,
            "demand_model": expected_demand["model"],
            "season": expected_demand.get("season"),
            "recommendation": recommendation,
            "redistribution_options": signal["redistribution_options"],
            "price_impact": price_impact,
        }

        if market_status != "balanced":
            alerts.append(signal)
        else:
            recommendations.append({
                "crop": crop,
                "status": market_status,
                "expected_demand_kg": expected_demand_kg,
                "supply_ratio": signal["supply_demand_ratio"],
                "message": signal["message"],
            })

        demand_by_crop[crop] = expected_demand_kg

    return {
        "analysis": supply_summary,
        "expected_demand": demand_by_crop,
        "crop_analysis": crop_analysis,
        "alerts": alerts,
        "recommendations": recommendations,
        "signals": signals,
    }


async def add_crop_listing(listing: CropListing, farmer_id: str = None) -> dict:
    """Store a listing. The stored document is returned under "listing" for broker matching."""
    doc = _listing_to_doc(listing, farmer_id)
    try:
        result = await market_collection.insert_one(doc)
        return {
            "success": True,
            "message": "Crop listing added successfully",
            "id": str(result.inserted_id),
            "listing": {**doc, "_id": str(result.inserted_id)},
        }
    except PyMongoError:
        doc.pop("_id", None)  # insert_one may have assigned one before failing
        inserted_id = await local_market_store.insert_listing(doc)
        return {
            "success": True,
            "message": "Crop listing added successfully",
            "id": inserted_id,
            "storage": "local",
            "listing": {**doc, "_id": inserted_id},
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_all_listings() -> dict:
    try:
        cursor = market_collection.find({})
        listings = []
        async for doc in cursor:
            doc["_id"] = str(doc.get("_id", ""))
            if doc.get("created_at") is not None:
                doc["created_at"] = str(doc["created_at"])
            listings.append(doc)
        return {
            "success": True,
            "total": len(listings),
            "listings": listings,
        }
    except PyMongoError:
        listings = await local_market_store.find_listings()
        return {
            "success": True,
            "total": len(listings),
            "listings": listings,
            "storage": "local",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_regional_supply(region: str) -> dict:
    region_key = normalize_key(region)
    storage = "mongodb"
    try:
        cursor = market_collection.find({
            "location": region_key,
            "status": "available",
        })

        listings = []
        async for doc in cursor:
            listings.append(doc)
        supply = _build_supply_summary_from_listings(listings)
    except PyMongoError:
        listings = await local_market_store.find_listings({
            "location": region_key,
            "status": "available",
        })
        supply = _build_supply_summary_from_listings(listings)
        storage = "local"
    except Exception as e:
        return {"success": False, "error": str(e)}

    is_demo = not supply
    if is_demo:
        supply = _build_demo_supply_summary(region_key)

    return {
        "success": True,
        "region": region_key,
        "crops_available": len(supply),
        "supply": supply,
        "source": "demo_estimate" if is_demo and supply else "farmer_listings",
        "is_demo": is_demo and bool(supply),
        "storage": storage,
    }


async def get_all_regional_supply() -> dict:
    storage = "mongodb"
    try:
        cursor = market_collection.find({"status": "available"})
        listings = [listing async for listing in cursor]
    except PyMongoError:
        listings = await local_market_store.find_listings({"status": "available"})
        storage = "local"
    except Exception as e:
        return {"success": False, "error": str(e)}

    regional_supply = _build_regional_supply_summary_from_listings(listings)
    is_demo = not regional_supply
    if is_demo:
        demo_data = _seed_demo_regional_data()
        regional_supply = {
            region: _build_demo_supply_summary(region)
            for region in demo_data
        }

    return {
        "success": True,
        "regional_supply": regional_supply,
        "total_regions": len(regional_supply),
        "total_listings": sum(
            crop_data["listings_count"]
            for crops in regional_supply.values()
            for crop_data in crops.values()
        ),
        "source": "demo_estimate" if is_demo and regional_supply else "farmer_listings",
        "is_demo": is_demo and bool(regional_supply),
        "storage": storage,
    }


async def analyze_demand(region: str, crop_name: str = None) -> dict:
    try:
        region_key = normalize_key(region)
        regional_data, storage = await _load_supply_index_any_storage()
        regional_data, is_demo = _with_demo_fallback(regional_data)

        # Only this region's own listings are analysed. A region with no
        # listings gets an empty analysis, never another region's data.
        supply_summary = dict(regional_data.get(region_key, {}))
        if crop_name:
            crop_key = normalize_key(crop_name)
            supply_summary = {crop_key: supply_summary.get(crop_key, 0)}

        result = _build_demand_result(region_key, supply_summary, regional_data)

        # Demo signals must not be persisted as if they were real alerts.
        if storage == "mongodb" and not is_demo:
            try:
                await _save_alert_history(result["signals"])
            except PyMongoError:
                storage = "local"

        message = None
        if not result["crop_analysis"]:
            message = f"No available farmer listings found for '{region.strip()}'."

        return {
            "success": True,
            "region": region_key,
            **result,
            "thresholds": DEMAND_THRESHOLDS,
            "total_alerts": len(result["alerts"]),
            "is_demo": is_demo,
            "source": "demo_estimate" if is_demo else "farmer_listings",
            "generated_at": _utc_now_iso(),
            "storage": storage,
            "message": message,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_market_summary() -> dict:
    storage = "mongodb"
    try:
        try:
            listings = [doc async for doc in market_collection.find({"status": "available"})]
        except PyMongoError:
            listings = await local_market_store.find_listings({"status": "available"})
            storage = "local"

        regional_data = _build_regional_data_from_listings(listings)
        return {
            "success": True,
            "total_listings": len(listings),
            "total_quantity_kg": round(
                sum(float(doc.get("quantity_kg") or 0) for doc in listings), 2
            ),
            "regions_active": len(regional_data),
            "regional_summary": regional_data,
            "thresholds": DEMAND_THRESHOLDS,
            "generated_at": _utc_now_iso(),
            "storage": storage,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_all_market_alerts() -> dict:
    try:
        regional_data, storage = await _load_supply_index_any_storage()
        regional_data, is_demo = _with_demo_fallback(regional_data)

        signals = []
        for region, crops in regional_data.items():
            signals.extend(
                _build_demand_result(region, crops, regional_data)["signals"]
            )

        if storage == "mongodb" and not is_demo:
            try:
                await _save_alert_history(signals)
            except PyMongoError:
                storage = "local"

        return {
            "success": True,
            "total": len(signals),
            "high_alerts": sum(signal["severity"] == "high" for signal in signals),
            "medium_alerts": sum(signal["severity"] == "medium" for signal in signals),
            "alerts": signals,
            "is_demo": is_demo,
            "source": "demo_estimate" if is_demo else "farmer_listings",
            "generated_at": _utc_now_iso(),
            "storage": storage,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
