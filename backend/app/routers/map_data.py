"""Read-only map API (Phase 7.5 support).

Thin: it only shapes existing data for the map. Machine status is derived from
today's MachineAvailability slot (with a maintenance override); shortage zones
reuse the demand engine's shortages + cluster centroids. No new intelligence.
Mounted at /api/map.
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CHC, Machine, MachineAvailability
from app.schemas.map_data import MapMachine, MapShortage
from app.services.demand_engine import analyze_demand, build_clusters, get_shortages

router = APIRouter(prefix="/map", tags=["Map"])


@router.get("/machines", response_model=list[MapMachine])
def map_machines(db: Session = Depends(get_db)):
    """All machines with their live status for the map (colored markers)."""
    today = date.today()
    todays_status = dict(
        db.execute(
            select(MachineAvailability.machine_id, MachineAvailability.status)
            .where(MachineAvailability.date == today)
        ).all()
    )
    chc_names = {c.id: c.name for c in db.scalars(select(CHC)).all()}

    out: list[MapMachine] = []
    for m in db.scalars(select(Machine)).all():
        if m.maintenance_status == "maintenance":
            status = "maintenance"
        else:
            status = todays_status.get(m.id, "available")
        out.append(MapMachine(
            id=m.id,
            machine_type=m.machine_type,
            chc_id=m.chc_id,
            chc_name=chc_names.get(m.chc_id, ""),
            latitude=m.current_latitude,
            longitude=m.current_longitude,
            status=status,
        ))
    return out


@router.get("/shortages", response_model=list[MapShortage])
def map_shortages(db: Session = Depends(get_db)):
    """High-risk shortage zones (placed at their cluster centroid)."""
    centroids, _ = build_clusters(db)
    shortages = get_shortages(analyze_demand(db), min_risk="HIGH")

    out: list[MapShortage] = []
    for s in shortages:
        lat, lon = centroids.get(s.cluster, (0.0, 0.0))
        out.append(MapShortage(
            cluster=s.cluster,
            latitude=lat,
            longitude=lon,
            machine_type=s.machine_type,
            risk_level=s.risk_level,
            shortage_probability=s.shortage_probability,
            expected_requests=s.expected_requests,
            available_supply=s.available_supply,
        ))
    return out
