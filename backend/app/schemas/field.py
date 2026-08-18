"""Pydantic schemas for Field (request/response shapes)."""
from pydantic import BaseModel, ConfigDict, Field


class FieldBase(BaseModel):
    farmer_id: int = Field(..., gt=0, description="ID of the farmer who owns this field")
    crop_type: str = Field(..., min_length=1, max_length=80)
    area: float = Field(0.0, ge=0, description="Field area in acres")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class FieldCreate(FieldBase):
    """Payload to create a Field."""


class FieldUpdate(BaseModel):
    """Partial update - only the fields you send are changed."""

    farmer_id: int | None = Field(None, gt=0)
    crop_type: str | None = Field(None, min_length=1, max_length=80)
    area: float | None = Field(None, ge=0)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


class FieldRead(FieldBase):
    """What the API returns for a Field."""

    model_config = ConfigDict(from_attributes=True)

    id: int
