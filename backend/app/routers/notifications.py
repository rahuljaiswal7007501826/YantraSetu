"""In-app notifications. Mounted at /api/me/notifications.

Role-agnostic: any authenticated user (Farmer / CHC Manager / Operator / Admin),
owner-scoped to their own user_id. This is the same owner-scoping idea as
/api/me/fields, but keyed on current_user.id instead of farmer_id, so it applies
to every role. Notifications are created internally via
notification_service.create_notification - there is no public create endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import Notification, User
from app.schemas.notification import NotificationRead, UnreadCount

router = APIRouter(prefix="/me/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The caller's own notifications, newest first."""
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
    return db.scalars(stmt).all()


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cheap unread count for the bell badge (kept separate from the list fetch)."""
    count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
    )
    return UnreadCount(unread=count or 0)


@router.post("/read-all", response_model=UnreadCount)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark every unread notification for the caller as read."""
    unread = db.scalars(
        select(Notification).where(
            Notification.user_id == current_user.id, Notification.is_read.is_(False)
        )
    ).all()
    for note in unread:
        note.is_read = True
    db.commit()
    return UnreadCount(unread=0)


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark one notification as read. Idempotent. Returns 404 if it isn't the
    caller's own (owner-scoping, not just role-scoping) so ids can't be probed."""
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found",
        )
    if not note.is_read:
        note.is_read = True
        db.commit()
        db.refresh(note)
    return note
