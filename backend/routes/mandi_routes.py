from fastapi import APIRouter, Depends, HTTPException, Query

from config.auth_deps import require_role
from services.mandi.analytics import data_health, list_markets, weekly_price_history
from services.mandi.config import COMMODITIES, resolve_commodity
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


@router.get("/market/demand/alerts", dependencies=[Depends(require_role("broker"))])
async def demand_alerts(since: str = None, commodity: str = None, limit: int = Query(100, ge=1, le=500)):
    cid = _commodity_or_404(commodity) if commodity else None
    alerts = await (await get_store()).find_alerts(since=since, commodity=cid, limit=limit)
    for alert in alerts:
        alert["id"] = str(alert.pop("_id", ""))
    return {"success": True, "total": len(alerts), "alerts": alerts}


@router.get("/market/prices/markets", dependencies=[Depends(require_role("broker"))])
async def price_markets(commodity: str, state: str = None, days: int = Query(90, ge=1, le=3650)):
    cid = _commodity_or_404(commodity)
    markets = await list_markets(await get_store(), cid, state=state, days=days)
    return {"success": True, "commodity": cid, "total": len(markets), "markets": markets}
