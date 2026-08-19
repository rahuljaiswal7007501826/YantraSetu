"""Booking model.

A Booking ties one DemandRequest to the specific Machine a manager assigned to
it. There is at most one booking per request (demand_request_id is unique). It
also carries the scheduling detail a Route will later fill in, plus who assigned
it and when.

status (string, like the rest of the app):
  active - the assignment is live (request is allocated / scheduled)
  voided - the assignment was withdrawn (request rejected or cancelled)
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BookingStatus(str, enum.Enum):
    ACTIVE = "active"
    VOIDED = "voided"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    # One booking per request.
    demand_request_id: Mapped[int] = mapped_column(
        ForeignKey("demand_requests.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BookingStatus.ACTIVE.value
    )
    # Filled in when a future phase places this booking into a concrete route.
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    route_id: Mapped[int | None] = mapped_column(
        ForeignKey("routes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Who assigned it (manager/admin) and when. SET NULL so deleting a user
    # keeps the booking's history intact.
    assigned_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} req={self.demand_request_id} "
            f"machine={self.machine_id} status={self.status}>"
        )
