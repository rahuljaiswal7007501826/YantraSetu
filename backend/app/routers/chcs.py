"""CRUD endpoints for CHCs (Custom Hiring Centres). Mounted at /api/chcs."""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models import CHC, UserRole
from app.schemas import CHCCreate, CHCRead, CHCUpdate
from app.utils import get_or_404

# Reads (list/get) allowed for operators too; writes are further restricted
# to managers + admins on the individual write endpoints (Phase I-B).
router = APIRouter(
    prefix="/chcs",
    tags=["CHCs"],
    dependencies=[Depends(require_roles(UserRole.OPERATOR, UserRole.CHC_MANAGER, UserRole.ADMIN))],
)

# Write operations (create/update/delete) require managers or admins. This is an
# ADDITIONAL guard on top of the router-level read guard above.
_manager_only = require_roles(UserRole.CHC_MANAGER, UserRole.ADMIN)


@router.get("", response_model=list[CHCRead])
def list_chcs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List CHCs (simple offset/limit pagination)."""
    return db.scalars(select(CHC).order_by(CHC.id).offset(skip).limit(limit)).all()


@router.post("", response_model=CHCRead, status_code=status.HTTP_201_CREATED)
def create_chc(payload: CHCCreate, db: Session = Depends(get_db), _guard=Depends(_manager_only)):
    """Create a CHC."""
    chc = CHC(**payload.model_dump())
    db.add(chc)
    db.commit()
    db.refresh(chc)
    return chc


@router.get("/{chc_id}", response_model=CHCRead)
def get_chc(chc_id: int, db: Session = Depends(get_db)):
    """Fetch a single CHC by id."""
    return get_or_404(db, CHC, chc_id, "CHC")


@router.put("/{chc_id}", response_model=CHCRead)
def update_chc(
    chc_id: int, payload: CHCUpdate, db: Session = Depends(get_db),
    _guard=Depends(_manager_only),
):
    """Partially update a CHC - only the fields present in the body change."""
    chc = get_or_404(db, CHC, chc_id, "CHC")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(chc, key, value)
    db.commit()
    db.refresh(chc)
    return chc


@router.delete("/{chc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chc(chc_id: int, db: Session = Depends(get_db), _guard=Depends(_manager_only)):
    """Delete a CHC (its machines are removed too, via cascade)."""
    chc = get_or_404(db, CHC, chc_id, "CHC")
    db.delete(chc)
    db.commit()
