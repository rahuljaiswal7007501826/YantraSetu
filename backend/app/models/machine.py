"""Machine model.

A single piece of agricultural machinery (e.g. a combine harvester) that belongs
to a CHC. Machines are what we allocate, schedule, and relocate. Its live
location (current_latitude/longitude) lets us show it moving on the map later.
"""
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.chc import CHC
    from app.models.machine_availability import MachineAvailability


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Foreign key -> which CHC owns this machine. Indexed because we query
    # "all machines for a CHC" constantly.
    chc_id: Mapped[int] = mapped_column(
        ForeignKey("chcs.id"), nullable=False, index=True
    )
    machine_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    capacity: Mapped[float] = mapped_column(Float, default=0.0)          # e.g. acres/hour
    operating_radius: Mapped[float] = mapped_column(Float, default=0.0)  # in km
    # "operational" or "maintenance". Kept as a string for now; we may promote
    # it to a strict enum once the availability logic needs it.
    maintenance_status: Mapped[str] = mapped_column(String(30), default="operational")
    current_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    current_longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationship: many machines -> one CHC.
    chc: Mapped["CHC"] = relationship(back_populates="machines")
    # One machine has many availability slots (per day/time window).
    availability: Mapped[list["MachineAvailability"]] = relationship(
        back_populates="machine", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Machine id={self.id} type={self.machine_type!r} chc_id={self.chc_id}>"
