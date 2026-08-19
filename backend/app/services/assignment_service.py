"""Assignment workflow orchestration (Phase 16).

The three side effects of a manager acting on a request live here in one place:
  * create / void the Booking that pins a machine to the request,
  * transition DemandRequest.status,
  * notify the farmer via the Phase 15 notification primitive.

Machine selection (direct pick vs the allocation engine) is decided by the
router; this service only records the decision. Each function commits its own
unit of work. Notifying the farmer is best-effort - most synthetic farmers have
no login account, and a missing account never fails the workflow.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, DemandRequest, Machine, User
from app.models.booking import BookingStatus
from app.models.notification import NotificationType
from app.services.notification_service import create_notification


def _notify_farmer(db: Session, request: DemandRequest, *, type, title, body, link) -> None:
    """Notify the farmer's login account, if one is linked to their profile."""
    user = db.scalar(select(User).where(User.farmer_id == request.farmer_id))
    if user is not None:
        create_notification(
            db, user_id=user.id, type=type, title=title, body=body,
            link=link, related_id=request.id,
        )


def assign_machine(
    db: Session, *, request: DemandRequest, machine: Machine, assigned_by_user_id: int
) -> Booking:
    """Assign `machine` to `request`: upsert the Booking (one per request, so a
    re-assign updates it in place), set status=allocated, notify the farmer."""
    booking = db.scalar(select(Booking).where(Booking.demand_request_id == request.id))
    now = datetime.now(timezone.utc)
    if booking is None:
        booking = Booking(
            demand_request_id=request.id,
            machine_id=machine.id,
            status=BookingStatus.ACTIVE.value,
            assigned_by_user_id=assigned_by_user_id,
            assigned_at=now,
        )
        db.add(booking)
    else:
        booking.machine_id = machine.id
        booking.status = BookingStatus.ACTIVE.value
        booking.assigned_by_user_id = assigned_by_user_id
        booking.assigned_at = now

    request.status = "allocated"
    db.flush()
    _notify_farmer(
        db, request,
        type=NotificationType.REQUEST_ASSIGNED,
        title="A machine has been assigned",
        body=f"A {machine.machine_type} has been assigned to your {request.operation_type} request.",
        link="/my-booking",
    )
    db.commit()
    db.refresh(booking)
    return booking


def reject_request(db: Session, *, request: DemandRequest, reason: str) -> None:
    """Reject a request with a reason; void any booking; notify the farmer."""
    request.status = "rejected"
    booking = db.scalar(select(Booking).where(Booking.demand_request_id == request.id))
    if booking is not None:
        booking.status = BookingStatus.VOIDED.value
    _notify_farmer(
        db, request,
        type=NotificationType.REQUEST_REJECTED,
        title="Your request could not be fulfilled",
        body=f"Your {request.operation_type} request was rejected. Reason: {reason}",
        link="/my-requests",
    )
    db.commit()


def cancel_request(db: Session, *, request: DemandRequest) -> None:
    """Cancel a request; void any booking; notify the farmer.

    No route recompute here - bookings are not yet placed onto routes in this
    phase, so there is nothing to re-sequence.
    """
    request.status = "cancelled"
    booking = db.scalar(select(Booking).where(Booking.demand_request_id == request.id))
    if booking is not None:
        booking.status = BookingStatus.VOIDED.value
    _notify_farmer(
        db, request,
        type=NotificationType.REQUEST_CANCELLED,
        title="Your request was cancelled",
        body=f"Your {request.operation_type} request has been cancelled.",
        link="/my-requests",
    )
    db.commit()
