"""Shared helper utilities (geo distance, scoring helpers, HTTP helpers, ...)."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def get_or_404(db: Session, model: type, obj_id: int, name: str):
    """Fetch a row by primary key, or raise a clean 404.

    Keeps each router's "does this id exist?" check to one readable line:
        chc = get_or_404(db, CHC, chc_id, "CHC")
    """
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{name} with id={obj_id} not found",
        )
    return obj
