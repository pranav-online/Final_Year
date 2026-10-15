from fastapi import APIRouter, Depends, HTTPException, Query

from config.auth_deps import require_role
from services.mandi.analytics import data_health, list_markets, weekly_price_history
from services.mandi.config import COMMODITIES, resolve_commodity, state_key
from services.mandi.forecast import promoted_version
from services.mandi.insights import overview
from services.mandi.scheduler import scheduler_status
from services.mandi.store import get_store

router = APIRouter(tags=["Mandi Data"])


def _commodity_or_404(name: str) -> str:
    cid = resolve_commodity(name)
    if cid is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown commodity '{name}'. Supported: {', '.join(COMMODITIES)}",
        )
    return cid


@router.get("/health/data")
async def health_data():
    """Ingestion health: last pull per source, row counts, duplicates, staleness."""
    return await data_health(await get_store(), scheduler_status())


@router.get("/market/prices/commodities", dependencies=[Depends(require_role("broker"))])
async def price_commodities():
    return {
        "success": True,
        "commodities": [{"id": cid, "name": meta["name"], "tier": meta["tier"]}
                        for cid, meta in COMMODITIES.items()],
    }


@router.get("/market/prices/history", dependencies=[Depends(require_role("broker"))])
async def price_history(
    commodity: str,
    market_key: str = Query(None, description="state|district|market, from /market/prices/markets"),
    state: str = None,
    weeks: int = Query(52, ge=1, le=520),
):
    cid = _commodity_or_404(commodity)
    result = await weekly_price_history(await get_store(), cid, market_key=market_key,
                                        state=state, weeks=weeks)
    return {"success": True, "is_demo": False, "source": "mandi_prices", **result}


@router.get("/market/demand/overview", dependencies=[Depends(require_role("broker"))])
async def demand_overview(
    level: str = Query("state", pattern="^(national|state|market)$"),
    state: str = None,
    commodities: str = Query(None, description="comma-separated, e.g. tomato,onion"),
):
    """Pressure heatmap rows: inferred demand-supply quadrant, momentum, z-score, urgency, freshness."""
    wanted = [_commodity_or_404(c) for c in commodities.split(",")] if commodities else None
    result = await overview(await get_store(), level=level, state=state, commodities=wanted)
    return {"success": True, **result}


@router.get("/market/demand/alerts")
async def demand_alerts(since: str = None, commodity: str = None, limit: int = Query(100, ge=1, le=500),
                        user: dict = Depends(require_role("broker"))):
    """Market-wide alerts plus this broker's own listing matches."""
    cid = _commodity_or_404(commodity) if commodity else None
    alerts = await (await get_store()).find_alerts(since=since, commodity=cid, limit=limit,
                                                   broker_id=user["sub"])
    for alert in alerts:
        alert["id"] = str(alert.pop("_id", ""))
    return {"success": True, "total": len(alerts), "alerts": alerts}


@router.get("/market/demand/forecast/{commodity}", dependencies=[Depends(require_role("broker"))])
async def demand_forecast(
    commodity: str,
    level: str = Query("national", pattern="^(national|state|market)$"),
    scope: str = Query(None, description="state name or market_key; omit for India"),
):
    """P10/P50/P90 at 1, 2 and 4 weeks, or 'Not enough signal' when the series failed the backtest."""
    cid = _commodity_or_404(commodity)
    if level == "national":
        scope_key = "india"
    elif not scope:
        raise HTTPException(status_code=422, detail=f"'scope' is required for level={level}")
    else:
        scope_key = state_key(scope) if level == "state" else scope.strip().lower()

    docs = await (await get_store()).find_scoped("forecasts", cid, level, scope_key)
    if not docs:
        raise HTTPException(status_code=404, detail=f"No forecast for {cid} at {level} '{scope_key}' yet")
    doc = docs[0]
    doc.pop("_id", None)
    doc["display"] = (
        "Not enough signal" if doc["confidence"] == "insufficient"
        else "8 in 10 times the price lands between P10 and P90"
    )
    return {"success": True, "is_demo": False, **doc}


@router.get("/market/demand/model", dependencies=[Depends(require_role("broker"))])
async def forecast_model():
    """Model registry: latest training run, its backtest and promotion decision, and the version in use."""
    store = await get_store()
    registry = sorted(await store.get_master("model_registry"), key=lambda r: r["_id"])
    return {
        "success": True,
        "in_use": await promoted_version(store),
        "latest_run": registry[-1] if registry else None,
        "runs": len(registry),
    }


@router.get("/market/prices/markets", dependencies=[Depends(require_role("broker"))])
async def price_markets(commodity: str, state: str = None, days: int = Query(90, ge=1, le=3650)):
    cid = _commodity_or_404(commodity)
    markets = await list_markets(await get_store(), cid, state=state, days=days)
    return {"success": True, "commodity": cid, "total": len(markets), "markets": markets}
