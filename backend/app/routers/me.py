"""Farmer self-service endpoints. Mounted at /api/me.

Every endpoint here is restricted to the FARMER role and scoped to the caller's
own linked Farmer profile (current_user.farmer_id). These are read-only,
farmer-facing views:

  GET /api/me/fields                        - the farmer's own fields
  GET /api/me/requests/{id}/assignment      - the machine recommended for the
                                              farmer's own request

Staff manage fields and run allocation through their own endpoints; nothing here
exposes the staff allocation endpoint or duplicates allocation logic - the
assignment view reuses the existing allocation engine.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.database import get_db
from app.models import CHC, Booking, DemandRequest, Field, Machine, User, UserRole
from app.schemas.field import FieldRead
from app.schemas.me import MyAssignedMachine, MyAssignmentRead
from app.services.allocation_engine import recommend_machines
from app.utils.geo import haversine_km

router = APIRouter(prefix="/me", tags=["Farmer Self-Service"])


@router.get("/fields", response_model=list[FieldRead])
def my_fields(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.FARMER)),
):
    """The current farmer's own fields (used by the New Request form)."""
    if current_user.farmer_id is None:
        return []
    return db.scalars(
        select(Field)
        .where(Field.farmer_id == current_user.farmer_id)
        .order_by(Field.id)
    ).all()


@router.get("/requests/{request_id}/assignment", response_model=MyAssignmentRead)
def my_assignment(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.FARMER)),
):
    """Read-only view of the machine recommended for the farmer's OWN request.

    Reuses the allocation engine (no logic duplicated) and never exposes the
    staff allocation endpoint. Returns 404 if the request is not the caller's own
    (so request ids cannot be enumerated).
    """
    req = db.get(DemandRequest, request_id)
    if req is None or current_user.farmer_id is None or req.farmer_id != current_user.farmer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found",
        )

    # If a real Booking exists (Phase 16 assignment), that machine is
    # authoritative - show it instead of a live recommendation preview.
    booking = db.scalar(
        select(Booking).where(
            Booking.demand_request_id == request_id, Booking.status == "active"
        )
    )
    if booking is not None:
        machine = db.get(Machine, booking.machine_id)
        if machine is None:
            return MyAssignmentRead(
                request_id=req.id, status=req.status, assigned_machine=None,
                message="Your assigned machine is being confirmed.",
            )
        chc = db.get(CHC, machine.chc_id)
        field = db.get(Field, req.field_id)
        distance = (
            round(
                haversine_km(field.latitude, field.longitude,
                             machine.current_latitude, machine.current_longitude),
                1,
            )
            if field else 0.0
        )
        return MyAssignmentRead(
            request_id=req.id, status=req.status,
            assigned_machine=MyAssignedMachine(
                machine_id=machine.id, machine_type=machine.machine_type,
                chc_name=chc.name if chc else "", distance_km=distance, compatible=True,
            ),
            message=None,
        )

    # Terminal states have no live assignment to preview.
    if req.status in ("rejected", "cancelled", "completed"):
        return MyAssignmentRead(
            request_id=req.id, status=req.status, assigned_machine=None,
            message=f"This request was {req.status}.",
        )

    try:
        candidates = recommend_machines(db, request_id, top_n=1)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not compute your assignment right now. Please retry.",
        )

    top = (candidates or [None])[0]
    if top is None:
        return MyAssignmentRead(
            request_id=req.id,
            status=req.status,
            assigned_machine=None,
            message="No machine is available for your request yet. The network is looking for one.",
        )
    return MyAssignmentRead(
        request_id=req.id,
        status=req.status,
        assigned_machine=MyAssignedMachine(
            machine_id=top.machine_id,
            machine_type=top.machine_type,
            chc_name=top.chc_name,
            distance_km=top.distance_km,
            compatible=top.compatible,
        ),
        message=None,
    )
