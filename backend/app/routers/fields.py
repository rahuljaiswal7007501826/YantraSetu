"""CRUD endpoints for Fields. Mounted at /api/fields."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Farmer, Field
from app.schemas import FieldCreate, FieldRead, FieldUpdate
from app.utils import get_or_404

router = APIRouter(prefix="/fields", tags=["Fields"])


def _ensure_farmer_exists(db: Session, farmer_id: int) -> None:
    """A field must belong to a real farmer - give a clear 400 if it doesn't."""
    if db.get(Farmer, farmer_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Farmer with id={farmer_id} does not exist",
        )


@router.get("", response_model=list[FieldRead])
def list_fields(
    farmer_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List fields, optionally filtered by their owning farmer (?farmer_id=)."""
    stmt = select(Field).order_by(Field.id)
    if farmer_id is not None:
        stmt = stmt.where(Field.farmer_id == farmer_id)
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("", response_model=FieldRead, status_code=status.HTTP_201_CREATED)
def create_field(payload: FieldCreate, db: Session = Depends(get_db)):
    """Create a field. The referenced farmer must already exist."""
    _ensure_farmer_exists(db, payload.farmer_id)
    field = Field(**payload.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.get("/{field_id}", response_model=FieldRead)
def get_field(field_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Field, field_id, "Field")


@router.put("/{field_id}", response_model=FieldRead)
def update_field(field_id: int, payload: FieldUpdate, db: Session = Depends(get_db)):
    field = get_or_404(db, Field, field_id, "Field")
    data = payload.model_dump(exclude_unset=True)
    if "farmer_id" in data:
        _ensure_farmer_exists(db, data["farmer_id"])
    for key, value in data.items():
        setattr(field, key, value)
    db.commit()
    db.refresh(field)
    return field


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(field_id: int, db: Session = Depends(get_db)):
    field = get_or_404(db, Field, field_id, "Field")
    db.delete(field)
    db.commit()
