from datetime import date
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum

class CropStatus(str, Enum):
    # Master report ERD: available | pending | sold
    available = "available"
    pending = "pending"
    sold = "sold"

class CropListing(BaseModel):
    farmer_name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    crop_name: str = Field(min_length=1)
    quantity_kg: float = Field(gt=0, allow_inf_nan=False)
    price_per_kg: float = Field(gt=0, allow_inf_nan=False)
    status: CropStatus = CropStatus.available
    contact: Optional[str] = None
    available_from: Optional[date] = None

    @field_validator("status", mode="before")
    @classmethod
    def legacy_reserved_is_pending(cls, value):
        # Older clients sent "reserved"; the report's lifecycle calls it "pending".
        return "pending" if value == "reserved" else value
