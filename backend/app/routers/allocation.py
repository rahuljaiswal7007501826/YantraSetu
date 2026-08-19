"""Allocation API - ranked machine recommendations for a demand request.

Thin layer: all compatibility + scoring lives in
app/services/allocation_engine.py. This router validates input, loads the
request context, calls the engine, and shapes the result. Mounted at
/api/allocation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models import DemandRequest, Farmer, UserRole
from app.schemas.allocation import (
    AllocationRequestIn,
    AllocationResponse,
    MachineRecommendation,
)
from app.services.allocation_engine import compatible_types, recommend_machines

# Allocation recommendations are a staff decision tool: managers + admins.
router = APIRouter(
    prefix="/allocation",
    tags=["Allocation"],
    dependencies=[Depends(require_roles(UserRole.CHC_MANAGER, UserRole.ADMIN))],
)


@router.post("/recommend", response_model=AllocationResponse)
def recommend_allocation(payload: AllocationRequestIn, db: Session = Depends(get_db)):
    """Return ranked, compatible machine candidates for a demand request.

    - 404 if the request id does not exist.
    - 200 with an empty list + `message` if no compatible/available machine exists.
    - 503 if the database is unreachable while computing.
    """
    # 1) Validate the request exists (and load related context).
    request = db.get(DemandRequest, payload.request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DemandRequest with id={payload.request_id} not found",
        )
    farmer = db.get(Farmer, request.farmer_id)

    # 2) Delegate the actual scoring to the engine (no logic duplicated here).
    try:
        candidates = recommend_machines(db, payload.request_id, top_n=payload.top_n)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error while computing recommendations. Please retry.",
        )
    candidates = candidates or []

    # 3) Explain the empty case clearly instead of returning a bare [].
    message = None
    if not candidates:
        if not compatible_types(request.operation_type):
            message = (f"No machine type is registered as compatible with "
                       f"operation '{request.operation_type}'.")
        else:
            message = (f"No compatible, operational machine with availability was "
                       f"found for operation '{request.operation_type}'.")

    return AllocationResponse(
        request_id=request.id,
        operation_type=request.operation_type,
        urgency=request.urgency,
        field_id=request.field_id,
        farmer_id=request.farmer_id,
        farmer_name=farmer.name if farmer else "",
        candidate_count=len(candidates),
        recommendations=[MachineRecommendation.from_candidate(c) for c in candidates],
        message=message,
    )
