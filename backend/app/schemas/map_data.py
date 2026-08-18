"""Pydantic schemas for the read-only map API (Phase 7.5 support)."""
from pydantic import BaseModel


class MapMachine(BaseModel):
    id: int
    machine_type: str
    chc_id: int
    chc_name: str
    latitude: float
    longitude: float
    # Derived current status: available | booked | in_transit | maintenance
    status: str


class MapShortage(BaseModel):
    cluster: str
    latitude: float          # cluster centroid, for drawing the zone
    longitude: float
    machine_type: str
    risk_level: str
    shortage_probability: float
    expected_requests: int
    available_supply: int
