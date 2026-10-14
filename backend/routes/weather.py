from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from services.weather_service import get_weather

router = APIRouter(prefix="/weather", tags=["Weather Advisory"])

@router.get("/advisory/{location}")
async def get_weather_advisory(
    location: str,
    disease: Optional[str] = Query(None, description="Recently detected plant disease"),
    severity: Optional[str] = Query(None, description="Severity level of the disease (high, medium, low)")
):
    result = await get_weather(location, disease=disease, severity=severity)

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail=result["error"]
        )

    return result