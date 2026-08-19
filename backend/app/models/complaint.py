"""Complaint model (Phase 19).

A farmer's complaint about a machine, an operator, a CHC's service, or general
service. It optionally references a past request / machine / CHC but never
requires one (a general-service complaint links to none of them).

Enums are stored as plain strings (same pattern as users.role /
demand_requests.status), with the Python enums documenting the allowed values -
so adding a value never needs a migration.

Lifecycle: open -> in_progress -> resolved -> closed.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ComplaintCategory(str, enum.Enum):
    """Allowed complaint categories. Stored as the string value in the DB."""

    MACHINE_NO_SHOW = "machine_no_show"
    MACHINE_BREAKDOWN = "machine_breakdown"
    WRONG_MACHINE_TYPE = "wrong_machine_type"
    OPERATOR_CONDUCT = "operator_conduct"
    CHC_SERVICE = "chc_service"
    OTHER = "other"


class ComplaintStatus(str, enum.Enum):
    """Complaint lifecycle. Stored as the string value in the DB."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Who filed it - the domain Farmer (matches DemandRequest.farmer_id). Owner
    # scoping compares this to User.farmer_id, exactly like requests / fields.
    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # One of ComplaintCategory values; stored as a string (like users.role).
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional context - a complaint may reference any / none of these. SET NULL
    # so deleting the referenced row keeps the complaint's history intact.
    demand_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("demand_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    machine_id: Mapped[int | None] = mapped_column(
        ForeignKey("machines.id", ondelete="SET NULL"), nullable=True
    )
    # Effective CHC: set directly, or derived from the linked machine at creation.
    # NULL = a general-service complaint (visible to ADMIN only).
    chc_id: Mapped[int | None] = mapped_column(
        ForeignKey("chcs.id", ondelete="SET NULL"), nullable=True
    )

    # One of ComplaintStatus values.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ComplaintStatus.OPEN.value, index=True
    )
    staff_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Which staff member last responded. SET NULL keeps history if they're removed.
    responded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        # The staff CHC queue query: WHERE chc_id = ? [AND status = ?].
        Index("ix_complaints_chc_status", "chc_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Complaint id={self.id} farmer_id={self.farmer_id} status={self.status}>"
