"""Pydantic schemas for bookings."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    demand_request_id: int
    machine_id: int
    status: str
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    route_id: int | None = None
    assigned_by_user_id: int | None = None
    assigned_at: datetime
