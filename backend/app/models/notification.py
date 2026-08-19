"""Notification model.

An in-app notification addressed to one user (the recipient). Other phases
create these through notification_service.create_notification(...); users read
only their own via /api/me/notifications (owner-scoped, role-agnostic).

The `type` is stored as a plain string (same pattern as users.role /
demand_requests.status), with NotificationType documenting the allowed values.
The composite index matches the query the bell runs constantly: filter by
user_id (and optionally is_read), newest first.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationType(str, enum.Enum):
    """Allowed notification kinds. Stored as the string value in the DB."""

    REQUEST_CREATED = "request_created"
    REQUEST_ASSIGNED = "request_assigned"
    REQUEST_REJECTED = "request_rejected"
    COMPLAINT_FILED = "complaint_filed"
    COMPLAINT_RESPONDED = "complaint_responded"
    COMPLAINT_RESOLVED = "complaint_resolved"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Recipient. CASCADE: if a user is deleted, their notifications go too.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # One of NotificationType values; stored as a string (like users.role).
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Frontend route to deep-link to, e.g. "/request/42". Nullable.
    link: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # id of the related DemandRequest/Complaint (for building/validating the link).
    related_id: Mapped[int | None] = mapped_column(nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        # The bell's constant query:
        #   WHERE user_id = ? [AND is_read = ?] ORDER BY created_at DESC
        Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} user_id={self.user_id} "
            f"type={self.type} read={self.is_read}>"
        )
