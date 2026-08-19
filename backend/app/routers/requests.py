"""Requests API (Phase 7.3 + 7.6).

Read endpoints (list/get) plus a thin create for the farmer's New Request form.
No intelligence here; the optional machine_type filter reuses the allocation
engine's COMPATIBILITY matrix. Mounted at /api/requests.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models import DemandRequest, Farmer, Field, Machine, User, UserRole
from app.models.notification import NotificationType
from app.schemas.booking import BookingRead
from app.schemas.request import (
    AssignRequestIn,
    DemandRequestCreate,
    DemandRequestRead,
    RejectRequestIn,
)
from app.services import assignment_service
from app.services.allocation_engine import COMPATIBILITY, compatible_types, recommend_machines
from app.services.notification_service import create_notification

# Requests are a farmer/staff workflow; operators are not part of it.
_REQUEST_ROLES = (UserRole.FARMER, UserRole.CHC_MANAGER, UserRole.ADMIN)
# Assignment / rejection are manager + admin actions (role-scoped; per-CHC
# scoping is a deferred follow-up - see docs/assumptions.md).
_STAFF_ROLES = (UserRole.CHC_MANAGER, UserRole.ADMIN)

router = APIRouter(prefix="/requests", tags=["Requests"])

RequestStatus = Literal["pending", "allocated", "scheduled", "completed", "cancelled", "rejected"]


def _to_read(req: DemandRequest, field: Field, farmer: Farmer) -> DemandRequestRead:
    return DemandRequestRead(
        id=req.id,
        farmer_id=req.farmer_id,
        farmer_name=farmer.name if farmer else "",
        field_id=req.field_id,
        crop_type=field.crop_type if field else "",
        village=farmer.village if farmer else "",
        latitude=field.latitude if field else 0.0,
        longitude=field.longitude if field else 0.0,
        operation_type=req.operation_type,
        urgency=req.urgency,
        requested_date=req.requested_date,
        status=req.status,
        created_at=req.created_at,
    )


def _notify_admins_of_new_request(db: Session, request: DemandRequest, farmer: Farmer) -> None:
    """Notify every ADMIN that a new request arrived (best-effort fan-out).

    Mirrors the complaint_filed pattern (Phase 19): there is no manager<->CHC
    link, so admins are the reliable staff recipients - a manager still sees the
    request in the pending queue. A missing recipient never fails creation.
    Flushes only (via the service); the caller owns the commit.
    """
    admins = db.scalars(select(User).where(User.role == UserRole.ADMIN.value)).all()
    for admin in admins:
        create_notification(
            db,
            user_id=admin.id,
            type=NotificationType.REQUEST_CREATED,
            title="New machinery request",
            body=f"{farmer.name} requested {request.operation_type} on {request.requested_date}.",
            link="/pending-requests",
            related_id=request.id,
        )


@router.get("", response_model=list[DemandRequestRead])
def list_requests(
    status_filter: RequestStatus | None = Query(None, alias="status"),
    operation_type: str | None = Query(None),
    machine_type: str | None = Query(
        None, description="Only requests whose operation this machine type can perform"
    ),
    farmer_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_REQUEST_ROLES)),
):
    stmt = (
        select(DemandRequest, Field, Farmer)
        .join(Field, Field.id == DemandRequest.field_id)
        .join(Farmer, Farmer.id == DemandRequest.farmer_id)
    )
    # Owner scoping: a FARMER only ever sees their own requests, regardless of any
    # farmer_id query value. Staff (manager/admin) may still filter by farmer_id.
    if current_user.role == UserRole.FARMER.value:
        if current_user.farmer_id is None:
            return []
        stmt = stmt.where(DemandRequest.farmer_id == current_user.farmer_id)
    elif farmer_id:
        stmt = stmt.where(DemandRequest.farmer_id == farmer_id)
    if status_filter:
        stmt = stmt.where(DemandRequest.status == status_filter)
    if operation_type:
        stmt = stmt.where(DemandRequest.operation_type == operation_type)
    if machine_type:
        ops = [op for op, types in COMPATIBILITY.items() if machine_type in types]
        if not ops:
            return []
        stmt = stmt.where(DemandRequest.operation_type.in_(ops))

    stmt = stmt.order_by(DemandRequest.id).limit(limit)
    return [_to_read(req, field, farmer) for req, field, farmer in db.execute(stmt).all()]


@router.post("", response_model=DemandRequestRead, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: DemandRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_REQUEST_ROLES)),
):
    """Create a machinery request for one of a farmer's fields.

    A FARMER may only create requests for their own linked profile (the payload's
    farmer_id is ignored for them). Staff (manager/admin) may create on behalf of
    any farmer.
    """
    if current_user.role == UserRole.FARMER.value:
        if current_user.farmer_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Your account is not linked to a farmer profile.",
            )
        farmer_id = current_user.farmer_id
    else:
        farmer_id = payload.farmer_id

    farmer = db.get(Farmer, farmer_id)
    if farmer is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Farmer {farmer_id} not found")
    field = db.get(Field, payload.field_id)
    if field is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Field {payload.field_id} not found")
    if field.farmer_id != farmer_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Field {payload.field_id} does not belong to farmer {farmer_id}",
        )

    req = DemandRequest(
        farmer_id=farmer_id,
        field_id=payload.field_id,
        operation_type=payload.operation_type,
        requested_date=payload.requested_date,
        urgency=payload.urgency,
        status="pending",
    )
    db.add(req)
    db.flush()  # assign req.id before creating notifications
    _notify_admins_of_new_request(db, req, farmer)
    db.commit()
    db.refresh(req)
    return _to_read(req, field, farmer)


@router.get("/{request_id}", response_model=DemandRequestRead)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_REQUEST_ROLES)),
):
    row = db.execute(
        select(DemandRequest, Field, Farmer)
        .join(Field, Field.id == DemandRequest.field_id)
        .join(Farmer, Farmer.id == DemandRequest.farmer_id)
        .where(DemandRequest.id == request_id)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DemandRequest with id={request_id} not found",
        )
    req, field, farmer = row
    # Owner scoping: a FARMER can only read their own request. Return 404 (not 403)
    # so request ids cannot be enumerated by non-owners.
    if current_user.role == UserRole.FARMER.value and req.farmer_id != current_user.farmer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DemandRequest with id={request_id} not found",
        )
    return _to_read(req, field, farmer)


# --------------------------------------------------------------------------- #
# Phase 16 - manager assignment workflow
#
# Role-scoped (any CHC_MANAGER/ADMIN may act on any pending request). Per-CHC
# manager scoping is a deliberate deferred follow-up - see docs/assumptions.md.
# The manager's "pending requests" list is the existing GET /api/requests?status=pending.
# --------------------------------------------------------------------------- #
@router.post("/{request_id}/assign", response_model=BookingRead)
def assign_request(
    request_id: int,
    payload: AssignRequestIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_STAFF_ROLES)),
):
    """Assign a machine to a request - directly (`machine_id`) or by assigning the
    top-ranked candidate from the allocation engine (`use_recommendation=true`).
    Both paths create/update the Booking and set the request to `allocated`."""
    req = db.get(DemandRequest, request_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"DemandRequest with id={request_id} not found")
    if req.status not in ("pending", "allocated"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot assign a request with status '{req.status}'.",
        )

    if payload.use_recommendation:
        # Reuse the allocation engine - do not duplicate its logic.
        try:
            candidates = recommend_machines(db, request_id, top_n=1)
        except SQLAlchemyError:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Database error while computing a recommendation. Please retry.",
            )
        if not candidates:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No compatible, available machine was found. Consider rejecting the request.",
            )
        machine = db.get(Machine, candidates[0].machine_id)
    else:
        if payload.machine_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Provide machine_id, or set use_recommendation=true.",
            )
        machine = db.get(Machine, payload.machine_id)
        if machine is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Machine {payload.machine_id} not found")
        # Compatibility is a hard gate (reuses the allocation engine's matrix).
        allowed = compatible_types(req.operation_type)
        if allowed and machine.machine_type not in allowed:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"A {machine.machine_type} cannot perform operation '{req.operation_type}'.",
            )

    if machine is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "The selected machine could not be loaded. Please retry."
        )

    return assignment_service.assign_machine(
        db, request=req, machine=machine, assigned_by_user_id=current_user.id
    )


@router.post("/{request_id}/reject", response_model=DemandRequestRead)
def reject_request(
    request_id: int,
    payload: RejectRequestIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_STAFF_ROLES)),
):
    """Reject a pending request with a required reason; notifies the farmer."""
    row = db.execute(
        select(DemandRequest, Field, Farmer)
        .join(Field, Field.id == DemandRequest.field_id)
        .join(Farmer, Farmer.id == DemandRequest.farmer_id)
        .where(DemandRequest.id == request_id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"DemandRequest with id={request_id} not found")
    req, field, farmer = row
    if req.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only a pending request can be rejected (status is '{req.status}').",
        )
    assignment_service.reject_request(db, request=req, reason=payload.reason)
    db.refresh(req)
    return _to_read(req, field, farmer)


@router.post("/{request_id}/cancel", response_model=DemandRequestRead)
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_REQUEST_ROLES)),
):
    """Cancel a request. A FARMER may cancel only their own; staff may cancel any.
    Voids the booking (if any) and notifies the farmer."""
    row = db.execute(
        select(DemandRequest, Field, Farmer)
        .join(Field, Field.id == DemandRequest.field_id)
        .join(Farmer, Farmer.id == DemandRequest.farmer_id)
        .where(DemandRequest.id == request_id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"DemandRequest with id={request_id} not found")
    req, field, farmer = row
    # Owner scoping: a FARMER may only cancel their own request (404, no enumeration).
    if current_user.role == UserRole.FARMER.value and req.farmer_id != current_user.farmer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"DemandRequest with id={request_id} not found")
    if req.status not in ("pending", "allocated", "scheduled"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot cancel a request with status '{req.status}'.",
        )
    assignment_service.cancel_request(db, request=req)
    db.refresh(req)
    return _to_read(req, field, farmer)
