"""Dashboard aggregation API (Phase 7.6).

Read-only KPI roll-ups for the Overview screen. No new intelligence:
  * machine status mirrors the map's derivation (today's slot, maintenance wins);
  * shortage counts reuse the demand engine;
  * relocation figures sum the pending recommendations.

Mounted at /api/dashboard.
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    CHC,
    DemandRequest,
    Farmer,
    Machine,
    MachineAvailability,
    RelocationRecommendation,
)
from app.schemas.dashboard import AdminDashboard
from app.services.demand_engine import analyze_demand, get_shortages

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/admin", response_model=AdminDashboard)
def admin_dashboard(db: Session = Depends(get_db)):
    # Current status per machine: today's availability slot, with maintenance
    # (a property of the machine itself) overriding everything.
    today = date.today()
    slot_status = dict(
        db.execute(
            select(MachineAvailability.machine_id, MachineAvailability.status).where(
                MachineAvailability.date == today
            )
        ).all()
    )
    counts = {"available": 0, "booked": 0, "in_transit": 0, "maintenance": 0}
    for machine_id, maintenance_status in db.execute(
        select(Machine.id, Machine.maintenance_status)
    ).all():
        current = (
            "maintenance"
            if maintenance_status == "maintenance"
            else slot_status.get(machine_id, "available")
        )
        counts[current] = counts.get(current, 0) + 1

    insights = analyze_demand(db)
    critical = sum(1 for i in insights if i.risk_level == "CRITICAL")
    high_risk = len(get_shortages(insights, "HIGH"))

    pending_relocs = db.scalars(
        select(RelocationRecommendation).where(
            RelocationRecommendation.status == "pending"
        )
    ).all()

    return AdminDashboard(
        total_chcs=db.scalar(select(func.count(CHC.id))),
        total_machines=db.scalar(select(func.count(Machine.id))),
        total_farmers=db.scalar(select(func.count(Farmer.id))),
        pending_requests=db.scalar(
            select(func.count(DemandRequest.id)).where(DemandRequest.status == "pending")
        ),
        machines_available=counts["available"],
        machines_booked=counts["booked"],
        machines_in_transit=counts["in_transit"],
        machines_maintenance=counts["maintenance"],
        critical_shortages=critical,
        high_risk_areas=high_risk,
        pending_relocations=len(pending_relocs),
        potential_net_benefit=sum(r.net_benefit for r in pending_relocs),
    )
