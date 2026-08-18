"""Pydantic schemas for Machine (request/response shapes)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Allowed values for a machine's health status. Using Literal gives us automatic
# validation plus a nice dropdown in the Swagger docs.
MaintenanceStatus = Literal["operational", "maintenance"]


class MachineBase(BaseModel):
    chc_id: int = Field(..., gt=0, description="ID of the CHC that owns this machine")
    machine_type: str = Field(..., min_length=1, max_length=80, description="e.g. Combine Harvester")
    capacity: float = Field(0.0, ge=0, description="Work capacity (unit depends on type)")
    operating_radius: float = Field(0.0, ge=0, description="Service radius in km")
    maintenance_status: MaintenanceStatus = "operational"
    current_latitude: float = Field(..., ge=-90, le=90)
    current_longitude: float = Field(..., ge=-180, le=180)


class MachineCreate(MachineBase):
    """Payload to create a Machine."""


class MachineUpdate(BaseModel):
    """Partial update - only the fields you send are changed."""

    chc_id: int | None = Field(None, gt=0)
    machine_type: str | None = Field(None, min_length=1, max_length=80)
    capacity: float | None = Field(None, ge=0)
    operating_radius: float | None = Field(None, ge=0)
    maintenance_status: MaintenanceStatus | None = None
    current_latitude: float | None = Field(None, ge=-90, le=90)
    current_longitude: float | None = Field(None, ge=-180, le=180)


class MachineRead(MachineBase):
    """What the API returns for a Machine."""

    model_config = ConfigDict(from_attributes=True)

    id: int
