from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from services.crop_service import recommend_crop
from services.geospatial_service import resolve_coordinates, get_soil_profile_for_coordinates

router = APIRouter(prefix="/crop", tags=["Crop Recommendation"])


class CropInput(BaseModel):
    location: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    season: str
    irrigation: Optional[str] = Field(default="rainfed")
    nitrogen: Optional[float] = Field(default=None, ge=0, le=300)
    phosphorous: Optional[float] = Field(default=None, ge=0, le=300)
    potassium: Optional[float] = Field(default=None, ge=0, le=400)
    ph: Optional[float] = Field(default=None, ge=2.5, le=12.0)
    temperature: Optional[float] = Field(default=None, ge=-20, le=65)
    humidity: Optional[float] = Field(default=None, ge=0, le=100)
    rainfall: Optional[float] = Field(default=None, ge=0, le=1500)

    @field_validator("season")
    @classmethod
    def normalize_season(cls, value: str) -> str:
        season = value.strip().lower()
        if season not in {"kharif", "rabi", "zaid"}:
            raise ValueError("Season must be kharif, rabi, or zaid.")
        return season

    @model_validator(mode="after")
    def check_location_or_coordinates(self):
        has_coords = self.latitude is not None and self.longitude is not None
        has_location = bool(self.location and self.location.strip())
        if not has_coords and not has_location:
            raise ValueError("Either farm map coordinates (latitude & longitude) or a location name must be provided.")
        return self


@router.post("/recommend")
async def get_crop_recommendation(data: CropInput):
    result = await recommend_crop(
        location=data.location,
        season=data.season,
        latitude=data.latitude,
        longitude=data.longitude,
        irrigation=data.irrigation,
        nitrogen=data.nitrogen,
        phosphorous=data.phosphorous,
        potassium=data.potassium,
        ph=data.ph,
        temperature=data.temperature,
        humidity=data.humidity,
        rainfall=data.rainfall,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to compute crop recommendation.")
        )

    return result


@router.get("/soil-profile")
async def get_soil_profile(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
):
    """
    Retrieves geospatial soil intelligence for selected map coordinates.
    Returns 250m gridded soil properties (ISRIC SoilGrids & Regional Survey)
    with explicit provenance, resolution, and uncertainty estimates.
    """
    try:
        geo = resolve_coordinates(latitude, longitude)
        profile = get_soil_profile_for_coordinates(
            latitude=latitude,
            longitude=longitude,
            district=geo.get("district"),
            state=geo.get("state"),
        )
        return {
            "success": True,
            "administrative_area": geo,
            "soil_profile": profile,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reverse-geocode")
async def reverse_geocode_location(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
):
    """
    Reverse geocodes coordinates to administrative district, state, country, and formatted address.
    """
    try:
        geo = resolve_coordinates(latitude, longitude)
        return {
            "success": True,
            "data": geo,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))