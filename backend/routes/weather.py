from fastapi import APIRouter, HTTPException
from services.weather_service import get_weather

router = APIRouter(prefix="/weather", tags=["Weather Advisory"])

@router.get("/advisory/{location}")
async def get_weather_advisory(location: str):
    result = await get_weather(location)

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail=result["error"]
        )

    return result