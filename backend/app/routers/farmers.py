"""CRUD endpoints for Farmers. Mounted at /api/farmers."""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models import Farmer, UserRole
from app.schemas import FarmerCreate, FarmerRead, FarmerUpdate
from app.utils import get_or_404

# Farmer records hold PII: staff only (managers + admins).
router = APIRouter(
    prefix="/farmers",
    tags=["Farmers"],
    dependencies=[Depends(require_roles(UserRole.CHC_MANAGER, UserRole.ADMIN))],
)


@router.get("", response_model=list[FarmerRead])
def list_farmers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.scalars(select(Farmer).order_by(Farmer.id).offset(skip).limit(limit)).all()


@router.post("", response_model=FarmerRead, status_code=status.HTTP_201_CREATED)
def create_farmer(payload: FarmerCreate, db: Session = Depends(get_db)):
    farmer = Farmer(**payload.model_dump())
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


@router.get("/{farmer_id}", response_model=FarmerRead)
def get_farmer(farmer_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Farmer, farmer_id, "Farmer")


@router.put("/{farmer_id}", response_model=FarmerRead)
def update_farmer(farmer_id: int, payload: FarmerUpdate, db: Session = Depends(get_db)):
    farmer = get_or_404(db, Farmer, farmer_id, "Farmer")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(farmer, key, value)
    db.commit()
    db.refresh(farmer)
    return farmer


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farmer(farmer_id: int, db: Session = Depends(get_db)):
    farmer = get_or_404(db, Farmer, farmer_id, "Farmer")
    db.delete(farmer)
    db.commit()
