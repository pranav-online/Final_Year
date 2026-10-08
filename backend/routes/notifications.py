from fastapi import APIRouter, HTTPException

from services.market_service import get_all_market_alerts


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/alerts")
async def get_alerts():
    result = await get_all_market_alerts()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result
