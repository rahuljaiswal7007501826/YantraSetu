"""Pydantic schemas for the route API (Phase 6, Step 3)."""
from datetime import datetime

from pydantic import BaseModel, Field


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


class RouteOptimizeRequest(BaseModel):
    """Body for POST /api/routes/optimize.

    The route is built for `machine_id`, visiting the farmers behind
    `request_ids`. This keeps the endpoint tied to real data, not the demo stops.
    """

    machine_id: int = Field(..., gt=0,
                            description="Machine that runs the route (depot = its location unless overridden)")
    request_ids: list[int] = Field(..., min_length=1, examples=[[151, 152, 153, 154]],
                                   description="DemandRequest ids (farmer stops) to visit")
    # Optional overrides:
    depot_lat: float | None = Field(None, ge=-90, le=90)
    depot_lon: float | None = Field(None, ge=-180, le=180)
    avg_speed_kmph: float | None = Field(None, gt=0)
    day_start_min: int | None = Field(None, ge=0, le=1440)
    day_end_min: int | None = Field(None, ge=0, le=1440)
    default_service_min: int | None = Field(None, ge=0,
                                            description="Fallback service minutes when a field's area is tiny")


class RouteStopRead(BaseModel):
    sequence_number: int
    request_id: int | None
    is_depot: bool
    latitude: float
    longitude: float
    arrival_min: int
    arrival_clock: str
    service_start_min: int
    service_start_clock: str
    service_end_min: int
    service_duration_min: int

    @classmethod
    def from_stop(cls, s) -> "RouteStopRead":
        return cls(
            sequence_number=s.sequence_number,
            request_id=s.request_id,
            is_depot=s.is_depot,
            latitude=s.latitude,
            longitude=s.longitude,
            arrival_min=s.arrival_min,
            arrival_clock=_clock(s.arrival_min),
            service_start_min=s.service_start_min,
            service_start_clock=_clock(s.service_start_min),
            service_end_min=s.service_end_min,
            service_duration_min=s.service_duration_min,
        )


class RouteRead(BaseModel):
    id: int
    machine_id: int
    status: str
    depot_latitude: float
    depot_longitude: float
    total_distance_km: float
    total_travel_time_min: int
    total_route_duration_min: int
    returned_to_depot: bool
    dropped_stop_ids: list[int]
    stops: list[RouteStopRead]
    # Ordered [lat, lon] points for the frontend to draw the route line directly.
    path: list[list[float]]
    created_at: datetime

    @classmethod
    def from_route(cls, route) -> "RouteRead":
        return cls(
            id=route.id,
            machine_id=route.machine_id,
            status=route.status,
            depot_latitude=route.depot_latitude,
            depot_longitude=route.depot_longitude,
            total_distance_km=route.total_distance_km,
            total_travel_time_min=route.total_travel_time_min,
            total_route_duration_min=route.total_route_duration_min,
            returned_to_depot=route.returned_to_depot,
            dropped_stop_ids=route.dropped_stop_ids or [],
            stops=[RouteStopRead.from_stop(s) for s in route.stops],
            path=[[s.latitude, s.longitude] for s in route.stops],
            created_at=route.created_at,
        )
