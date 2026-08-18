"""MachineAvailability model.

One row = a machine's status for a specific day and time window. This is the raw
signal for "which machines are idle vs busy on a given date" - the input the
utilization engine uses, and how we spot idle machines worth relocating.
"""
from datetime import date as date_t, time as time_t
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.machine import Machine


class MachineAvailability(Base):
    __tablename__ = "machine_availability"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ondelete CASCADE: if a machine is removed, its slots go with it (DB-side).
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date_t] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time_t] = mapped_column(Time, nullable=False)
    end_time: Mapped[time_t] = mapped_column(Time, nullable=False)
    # available | booked | in_transit | maintenance
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available", index=True
    )

    machine: Mapped["Machine"] = relationship(back_populates="availability")

    def __repr__(self) -> str:
        return f"<MachineAvailability machine_id={self.machine_id} {self.date} {self.status}>"
