"""CHC (Custom Hiring Centre) model.

A CHC is a depot that owns machines and serves farmers in its area. It is the
"supply" side of YantraSetu - the place idle machines sit before we allocate or
relocate them.
"""
from typing import TYPE_CHECKING

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    # Imported only for type checkers, never at runtime (avoids a circular import).
    from app.models.machine import Machine


class CHC(Base):
    __tablename__ = "chcs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    # Stored as a simple "HH:MM-HH:MM" string for now; good enough for the demo.
    operating_hours: Mapped[str] = mapped_column(String(50), default="09:00-18:00")

    # Relationship: one CHC has many machines.
    # back_populates keeps both sides in sync; cascade means deleting a CHC
    # deletes its machines (fine for dev; we can tighten this later).
    machines: Mapped[list["Machine"]] = relationship(
        back_populates="chc",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CHC id={self.id} name={self.name!r}>"
