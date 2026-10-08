from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from services.crop_service import recommend_crop

router = APIRouter(prefix="/crop", tags=["Crop Recommendation"])

class CropInput(BaseModel):
    location: str = Field(min_length=1, max_length=120)
    season: str
    nitrogen: float | None = Field(default=None, ge=0, le=140)
    phosphorous: float | None = Field(default=None, ge=0, le=145)
    potassium: float | None = Field(default=None, ge=0, le=205)
    ph: float | None = Field(default=None, ge=3.5, le=10)
    temperature: float | None = Field(default=None, ge=0, le=50)
    humidity: float | None = Field(default=None, ge=0, le=100)
    rainfall: float | None = Field(default=None, ge=20, le=300)

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str) -> str:
        location = value.strip()
        if not location:
            raise ValueError("Location cannot be blank.")
        return location

    @field_validator("season")
    @classmethod
    def normalize_season(cls, value: str) -> str:
        season = value.strip().lower()
        if season not in {"kharif", "rabi", "zaid"}:
            raise ValueError("Season must be kharif, rabi, or zaid.")
        return season

@router.post("/recommend")
async def get_crop_recommendation(data: CropInput):
    result = await recommend_crop(
        location=data.location,
        season=data.season,
        nitrogen=data.nitrogen,
        phosphorous=data.phosphorous,
        potassium=data.potassium,
        ph=data.ph,
        temperature=data.temperature,
        humidity=data.humidity,
        rainfall=data.rainfall,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=result["error"]
        )

    return result