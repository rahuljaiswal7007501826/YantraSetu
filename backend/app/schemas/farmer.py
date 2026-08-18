"""Pydantic schemas for Farmer (request/response shapes)."""
from pydantic import BaseModel, ConfigDict, Field


class FarmerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    phone: str = Field(..., min_length=5, max_length=20)
    village: str = Field(..., min_length=1, max_length=120)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class FarmerCreate(FarmerBase):
    """Payload to create a Farmer."""


class FarmerUpdate(BaseModel):
    """Partial update - only the fields you send are changed."""

    name: str | None = Field(None, min_length=1, max_length=120)
    phone: str | None = Field(None, min_length=5, max_length=20)
    village: str | None = Field(None, min_length=1, max_length=120)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


class FarmerRead(FarmerBase):
    """What the API returns for a Farmer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
