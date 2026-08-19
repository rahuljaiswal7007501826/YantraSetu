"""Route API - optimize and persist a machine's route. Mounted at /api/routes.

Thin layer: all OR-Tools logic stays in app/services/route_engine.py. This
router validates input, loads DB data, builds the engine's Stop inputs, calls
the engine, and persists the Route + RouteStop rows.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models import DemandRequest, Field, Machine, Route, RouteStop, UserRole
from app.schemas.route import RouteOptimizeRequest, RouteRead
from app.services.route_engine import RouteConfig, Stop, optimize_route

# Route optimization + read: operators (who execute) plus managers + admins.
router = APIRouter(
    prefix="/routes",
    tags=["Routes"],
    dependencies=[Depends(require_roles(UserRole.OPERATOR, UserRole.CHC_MANAGER, UserRole.ADMIN))],
)

MINUTES_PER_ACRE = 15   # rough operation time per acre
MIN_SERVICE_MIN = 30    # never schedule a stop shorter than this


def _service_minutes(area: float | None, floor: int) -> int:
    return max(floor, round((area or 0) * MINUTES_PER_ACRE))


@router.post("/optimize", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
def optimize(payload: RouteOptimizeRequest, db: Session = Depends(get_db)):
    """Optimize and persist a route for a machine over the given farmer requests."""
    # 1) Validate the machine.
    machine = db.get(Machine, payload.machine_id)
    if machine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id={payload.machine_id} not found",
        )

    # 2) Load the requested farmer stops and reject any unknown ids.
    requests = db.scalars(
        select(DemandRequest).where(DemandRequest.id.in_(payload.request_ids))
    ).all()
    found = {r.id for r in requests}
    missing = [rid for rid in payload.request_ids if rid not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown DemandRequest id(s): {missing}",
        )
    fields = {
        f.id: f
        for f in db.scalars(
            select(Field).where(Field.id.in_([r.field_id for r in requests]))
        ).all()
    }

    # 3) Build the engine config + stops (translate DB rows -> engine inputs).
    overrides = {}
    if payload.avg_speed_kmph:
        overrides["avg_speed_kmph"] = payload.avg_speed_kmph
    if payload.day_start_min is not None:
        overrides["day_start_min"] = payload.day_start_min
    if payload.day_end_min is not None:
        overrides["day_end_min"] = payload.day_end_min
    config = RouteConfig(**overrides)
    floor = payload.default_service_min if payload.default_service_min is not None else MIN_SERVICE_MIN

    stops: list[Stop] = []
    for r in requests:
        field = fields.get(r.field_id)
        if field is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DemandRequest {r.id} has no field data to route to.",
            )
        stops.append(Stop(
            stop_id=r.id,
            lat=field.latitude,
            lon=field.longitude,
            open_min=config.day_start_min,
            close_min=config.day_end_min,
            service_min=_service_minutes(field.area, floor),
        ))

    depot = (
        payload.depot_lat if payload.depot_lat is not None else machine.current_latitude,
        payload.depot_lon if payload.depot_lon is not None else machine.current_longitude,
    )

    # 4) Delegate to the engine (no OR-Tools logic here).
    result = optimize_route(depot, stops, config)

    # 5) Persist the route and its ordered stops.
    try:
        route = Route(
            machine_id=machine.id,
            status="optimized",
            depot_latitude=depot[0],
            depot_longitude=depot[1],
            total_distance_km=result.total_distance_km,
            total_travel_time_min=result.total_travel_time_min,
            total_route_duration_min=result.total_route_duration_min,
            returned_to_depot=result.returned_to_depot,
            dropped_stop_ids=result.dropped_stop_ids,
        )
        for s in result.ordered_stops:
            route.stops.append(RouteStop(
                sequence_number=s.sequence,
                request_id=s.stop_id,
                is_depot=s.is_depot,
                latitude=s.lat,
                longitude=s.lon,
                arrival_min=s.arrival_min,
                service_start_min=s.service_start_min,
                service_end_min=s.service_end_min,
                service_duration_min=s.service_duration_min,
            ))
        db.add(route)
        db.commit()
        db.refresh(route)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error while saving the route. Please retry.",
        )

    return RouteRead.from_route(route)


@router.get("/{route_id}", response_model=RouteRead)
def get_route(route_id: int, db: Session = Depends(get_db)):
    """Fetch a saved route (with its ordered stops) by id."""
    route = db.get(Route, route_id)
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route with id={route_id} not found",
        )
    return RouteRead.from_route(route)
