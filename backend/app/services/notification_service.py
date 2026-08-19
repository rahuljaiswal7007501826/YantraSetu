"""Notification creation - the single place notifications are made.

Other phases (assignment updates, complaint responses, ...) import
create_notification(...) and call it inside their own request handler. It does a
plain insert and FLUSHES (assigns the id) but does NOT commit - the caller owns
the transaction, so a notification commits atomically with the event that caused
it (e.g. a request assignment and its "you've been assigned" notification either
both persist or both roll back). Callers that already commit (every existing
router does) get the notification saved for free.
"""
from sqlalchemy.orm import Session

from app.models import Notification
from app.models.notification import NotificationType


def create_notification(
    db: Session,
    *,
    user_id: int,
    type: NotificationType | str,
    title: str,
    body: str,
    link: str | None = None,
    related_id: int | None = None,
) -> Notification:
    """Insert a notification for one recipient and return it (id assigned).

    `type` accepts a NotificationType or its raw string value. Does not commit;
    the caller's transaction owns the commit.
    """
    type_value = type.value if isinstance(type, NotificationType) else str(type)
    note = Notification(
        user_id=user_id,
        type=type_value,
        title=title,
        body=body,
        link=link,
        related_id=related_id,
    )
    db.add(note)
    db.flush()  # assign the primary key without committing
    return note
