"""Pydantic schemas for the requests API (Phase 7.3 + 7.6)."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class DemandRequestRead(BaseModel):
    id: int
    farmer_id: int
    farmer_name: str
    field_id: int
    crop_type: str
    village: str
    latitude: float
    longitude: float
    operation_type: str
    urgency: str
    requested_date: date
    status: str
    created_at: datetime


class DemandRequestCreate(BaseModel):
    """Body for POST /api/requests (the farmer's New Request form)."""

    farmer_id: int = Field(..., gt=0)
    field_id: int = Field(..., gt=0)
    operation_type: str = Field(..., min_length=1, max_length=80)
    requested_date: date
    urgency: Literal["low", "medium", "high"] = "medium"
