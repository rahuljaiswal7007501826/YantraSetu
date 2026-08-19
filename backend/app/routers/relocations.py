"""Relocation API - the operator workflow over the relocation engine.

Endpoints (mounted at /api/relocations):
    POST /generate       - ask the engine to (re)compute pending recommendations
    GET  /               - list recommendations (optional ?status= filter)
    GET  /{id}           - one recommendation, with its financial breakdown
    POST /{id}/approve   - operator approves -> machine goes 'in_transit'
    POST /{id}/reject    - operator rejects  -> recommendation 'rejected'

The engine only ever proposes; approval/rejection is an explicit human action
here. Approving does NOT physically complete the move (the machine's home CHC
and coordinates are left unchanged); it only marks the machine in transit.
"""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models import MachineAvailability, RelocationRecommendation, UserRole
from app.schemas.relocation import GenerateResponse, RelocationRead
from app.services.relocation_engine import generate_recommendations

# Relocation workflow (view + generate + approve/reject): managers + admins.
router = APIRouter(
    prefix="/relocations",
    tags=["Relocations"],
    dependencies=[Depends(require_roles(UserRole.CHC_MANAGER, UserRole.ADMIN))],
)


def _get_or_404(db: Session, rec_id: int) -> RelocationRecommendation:
    rec = db.get(RelocationRecommendation, rec_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RelocationRecommendation with id={rec_id} not found",
        )
    return rec


@router.post("/generate", response_model=GenerateResponse)
def generate(db: Session = Depends(get_db)):
    """Run the relocation engine and persist any new pending recommendations."""
    try:
        created = generate_recommendations(db)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error while generating recommendations. Please retry.",
        )
    message = (
        f"Created {len(created)} new pending recommendation(s)."
        if created
        else "No new recommendations (none cleared the threshold, or they already exist as pending)."
    )
    return GenerateResponse(
        created_count=len(created),
        recommendations=[RelocationRead.from_rec(r) for r in created],
        message=message,
    )


@router.get("", response_model=list[RelocationRead])
def list_relocations(
    status_filter: Literal["pending", "approved", "rejected", "completed"] | None =
        Query(None, alias="status", description="Filter by recommendation status"),
    db: Session = Depends(get_db),
):
    """List relocation recommendations, most recent first, optionally filtered."""
    stmt = select(RelocationRecommendation).order_by(RelocationRecommendation.id.desc())
    if status_filter:
        stmt = stmt.where(RelocationRecommendation.status == status_filter)
    return [RelocationRead.from_rec(r) for r in db.scalars(stmt).all()]


@router.get("/{rec_id}", response_model=RelocationRead)
def get_relocation(rec_id: int, db: Session = Depends(get_db)):
    """Fetch one recommendation with its full financial breakdown."""
    return RelocationRead.from_rec(_get_or_404(db, rec_id))


@router.post("/{rec_id}/approve", response_model=RelocationRead)
def approve_relocation(rec_id: int, db: Session = Depends(get_db)):
    """Operator approves the move: mark it approved and set the machine in transit.

    Only a *pending* recommendation can be approved. This does not physically
    complete the relocation - the machine's home CHC/coordinates are unchanged.
    """
    rec = _get_or_404(db, rec_id)
    if rec.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve a recommendation with status '{rec.status}'. "
                   f"Only 'pending' recommendations can be approved.",
        )
    try:
        rec.status = "approved"
        # Mark the machine as in transit from today onward (it's leaving its cluster).
        db.execute(
            update(MachineAvailability)
            .where(
                MachineAvailability.machine_id == rec.machine_id,
                MachineAvailability.date >= date.today(),
            )
            .values(status="in_transit")
        )
        db.commit()
        db.refresh(rec)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error while approving. Please retry.",
        )
    return RelocationRead.from_rec(rec)


@router.post("/{rec_id}/reject", response_model=RelocationRead)
def reject_relocation(rec_id: int, db: Session = Depends(get_db)):
    """Operator rejects the move: mark it rejected. The machine is untouched."""
    rec = _get_or_404(db, rec_id)
    if rec.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject a recommendation with status '{rec.status}'. "
                   f"Only 'pending' recommendations can be rejected.",
        )
    try:
        rec.status = "rejected"
        db.commit()
        db.refresh(rec)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error while rejecting. Please retry.",
        )
    return RelocationRead.from_rec(rec)
