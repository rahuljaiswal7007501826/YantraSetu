"""CRUD endpoints for Machines. Mounted at /api/machines."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CHC, Machine
from app.schemas import MachineCreate, MachineRead, MachineUpdate
from app.utils import get_or_404

router = APIRouter(prefix="/machines", tags=["Machines"])


def _ensure_chc_exists(db: Session, chc_id: int) -> None:
    """A machine must belong to a real CHC - give a clear 400 if it doesn't."""
    if db.get(CHC, chc_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CHC with id={chc_id} does not exist",
        )


@router.get("", response_model=list[MachineRead])
def list_machines(
    chc_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List machines, optionally filtered by their owning CHC (?chc_id=)."""
    stmt = select(Machine).order_by(Machine.id)
    if chc_id is not None:
        stmt = stmt.where(Machine.chc_id == chc_id)
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("", response_model=MachineRead, status_code=status.HTTP_201_CREATED)
def create_machine(payload: MachineCreate, db: Session = Depends(get_db)):
    """Create a machine. The referenced CHC must already exist."""
    _ensure_chc_exists(db, payload.chc_id)
    machine = Machine(**payload.model_dump())
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


@router.get("/{machine_id}", response_model=MachineRead)
def get_machine(machine_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Machine, machine_id, "Machine")


@router.put("/{machine_id}", response_model=MachineRead)
def update_machine(machine_id: int, payload: MachineUpdate, db: Session = Depends(get_db)):
    machine = get_or_404(db, Machine, machine_id, "Machine")
    data = payload.model_dump(exclude_unset=True)
    if "chc_id" in data:
        _ensure_chc_exists(db, data["chc_id"])
    for key, value in data.items():
        setattr(machine, key, value)
    db.commit()
    db.refresh(machine)
    return machine


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    machine = get_or_404(db, Machine, machine_id, "Machine")
    db.delete(machine)
    db.commit()
