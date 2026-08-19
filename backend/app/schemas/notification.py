"""Pydantic schemas for notifications (read-only API shapes)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    """One notification as returned by the API. No recipient/user_id is exposed -
    the caller only ever sees their own rows, so it would be redundant."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    body: str
    link: str | None = None
    related_id: int | None = None
    is_read: bool
    created_at: datetime


class UnreadCount(BaseModel):
    """Payload for the bell badge."""

    unread: int
