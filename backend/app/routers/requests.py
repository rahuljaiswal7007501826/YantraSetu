"""Requests API (Phase 7.3 + 7.6).

Read endpoints (list/get) plus a thin create for the farmer's New Request form.
No intelligence here; the optional machine_type filter reuses the allocation
engine's COMPATIBILITY matrix. Mounted at /api/requests.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DemandRequest, Farmer, Field
from app.schemas.request import DemandRequestCreate, DemandRequestRead
from app.services.allocation_engine import COMPATIBILITY

router = APIRouter(prefix="/requests", tags=["Requests"])

RequestStatus = Literal["pending", "allocated", "scheduled", "completed", "cancelled"]


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
):
    stmt = (
        select(DemandRequest, Field, Farmer)
        .join(Field, Field.id == DemandRequest.field_id)
        .join(Farmer, Farmer.id == DemandRequest.farmer_id)
    )
    if status_filter:
        stmt = stmt.where(DemandRequest.status == status_filter)
    if operation_type:
        stmt = stmt.where(DemandRequest.operation_type == operation_type)
    if farmer_id:
        stmt = stmt.where(DemandRequest.farmer_id == farmer_id)
    if machine_type:
        ops = [op for op, types in COMPATIBILITY.items() if machine_type in types]
        if not ops:
            return []
        stmt = stmt.where(DemandRequest.operation_type.in_(ops))

    stmt = stmt.order_by(DemandRequest.id).limit(limit)
    return [_to_read(req, field, farmer) for req, field, farmer in db.execute(stmt).all()]


@router.post("", response_model=DemandRequestRead, status_code=status.HTTP_201_CREATED)
def create_request(payload: DemandRequestCreate, db: Session = Depends(get_db)):
    """Create a machinery request for one of a farmer's fields."""
    farmer = db.get(Farmer, payload.farmer_id)
    if farmer is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Farmer {payload.farmer_id} not found")
    field = db.get(Field, payload.field_id)
    if field is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Field {payload.field_id} not found")
    if field.farmer_id != payload.farmer_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Field {payload.field_id} does not belong to farmer {payload.farmer_id}",
        )

    req = DemandRequest(
        farmer_id=payload.farmer_id,
        field_id=payload.field_id,
        operation_type=payload.operation_type,
        requested_date=payload.requested_date,
        urgency=payload.urgency,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _to_read(req, field, farmer)


@router.get("/{request_id}", response_model=DemandRequestRead)
def get_request(request_id: int, db: Session = Depends(get_db)):
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
    return _to_read(req, field, farmer)
