"""Demo scenario control (Phase 7.7).

A single reset endpoint so the deterministic SIH walkthrough can be re-run:
it returns any acted-on cross-CHC relocation recommendations to 'pending' and
undoes the 'in_transit' machine status that approval set, so the operator can
approve the move live again.

Only demo/seed state is touched and the engines are NOT re-run - this simply
rewinds the approve/reject action so the same story can be told repeatedly.
Mounted at /api/demo.
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MachineAvailability, RelocationRecommendation
from app.schemas.demo import DemoResetResult

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.post("/reset", response_model=DemoResetResult)
def reset_demo(db: Session = Depends(get_db)):
    """Rewind relocation decisions so the walkthrough starts fresh."""
    # Any recommendation that was approved/rejected goes back to pending.
    recs = db.scalars(
        select(RelocationRecommendation).where(
            RelocationRecommendation.status != "pending"
        )
    ).all()
    machine_ids = {r.machine_id for r in recs}
    for r in recs:
        r.status = "pending"

    # Undo the in_transit flag that approval set (today onward) back to available.
    # We only touch rows currently marked in_transit, so we don't clobber
    # unrelated booked/maintenance slots.
    restored_rows = 0
    if machine_ids:
        result = db.execute(
            update(MachineAvailability)
            .where(
                MachineAvailability.machine_id.in_(machine_ids),
                MachineAvailability.date >= date.today(),
                MachineAvailability.status == "in_transit",
            )
            .values(status="available")
        )
        restored_rows = result.rowcount or 0

    db.commit()

    return DemoResetResult(
        recommendations_reset=len(recs),
        machines_restored=len(machine_ids),
        availability_rows_restored=restored_rows,
        message=(
            f"Reset {len(recs)} recommendation(s) to pending and restored "
            f"{len(machine_ids)} machine(s) to available."
        ),
    )
