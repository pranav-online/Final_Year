from fastapi import APIRouter, Depends, HTTPException

from config.auth_deps import require_role
from services.market_service import get_all_market_alerts


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/alerts", dependencies=[Depends(require_role("broker"))])
async def get_alerts():
    result = await get_all_market_alerts()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result
