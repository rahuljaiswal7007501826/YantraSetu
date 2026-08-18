"""DemandRequest model.

A farmer's request for machinery on one of their fields: what operation, on what
date, how urgent, and where it is in its lifecycle. A cluster with many *pending*
requests and no suitable nearby machine is exactly the shortage YantraSetu must
detect and resolve - so this table is the heart of the "demand" signal.
"""
from datetime import date as date_t, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.farmer import Farmer
    from app.models.field import Field


class DemandRequest(Base):
    __tablename__ = "demand_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_id: Mapped[int] = mapped_column(
        ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    requested_date: Mapped[date_t] = mapped_column(Date, nullable=False, index=True)
    # low | medium | high
    urgency: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # pending | allocated | scheduled | completed | cancelled
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    farmer: Mapped["Farmer"] = relationship(back_populates="demand_requests")
    field: Mapped["Field"] = relationship(back_populates="demand_requests")

    def __repr__(self) -> str:
        return f"<DemandRequest id={self.id} op={self.operation_type!r} status={self.status}>"
