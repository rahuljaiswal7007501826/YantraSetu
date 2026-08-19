"""Complaints API (Phase 19). Mounted at /api (full paths per route).

Farmers file complaints (voice or text) about a machine, operator, CHC service,
or general service; staff (CHC_MANAGER / ADMIN) view, respond, resolve and close
them; the farmer sees the outcome and is notified.

Access model (matches Phase 16's role-scoped decision - there is no manager<->CHC
link):
  * Farmer  : only their own complaints (owner-scoped via current_user.farmer_id).
  * Staff   : GET /chc/{id}/complaints is role-gated (MANAGER/ADMIN) with the CHC
              id as an explicit filter (any manager/admin may query any CHC).
  * Admin   : GET /admin/complaints - everything, including general (chc_id NULL)
              complaints.

Notifications reuse the Phase 15 primitive. Because no manager<->CHC link exists,
a new complaint notifies all ADMIN accounts (best-effort, like the farmer
notifications) - managers still see complaints via the staff queue. See
docs/assumptions.md.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role, require_roles
from app.database import get_db
from app.models import CHC, Complaint, DemandRequest, Machine, User, UserRole
from app.models.notification import NotificationType
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintRead,
    ComplaintRespondIn,
    ComplaintStatusLiteral,
)
from app.services.notification_service import create_notification

router = APIRouter(tags=["Complaints"])

_STAFF_ROLES = (UserRole.CHC_MANAGER, UserRole.ADMIN)


def _notify_admins(db: Session, complaint: Complaint, *, title: str, body: str) -> None:
    """Notify every ADMIN account of a new complaint (best-effort fan-out).

    There is no manager<->CHC link, so admins are the reliable staff recipients;
    managers still see complaints via the staff queue. A missing recipient never
    fails the workflow.
    """
    admins = db.scalars(select(User).where(User.role == UserRole.ADMIN.value)).all()
    for admin in admins:
        create_notification(
            db,
            user_id=admin.id,
            type=NotificationType.COMPLAINT_FILED,
            title=title,
            body=body,
            link="/complaints",
            related_id=complaint.id,
        )


def _notify_farmer(db: Session, complaint: Complaint, *, type, title: str, body: str) -> None:
    """Notify the farmer's login account, if one is linked to their profile."""
    user = db.scalar(select(User).where(User.farmer_id == complaint.farmer_id))
    if user is not None:
        create_notification(
            db, user_id=user.id, type=type, title=title, body=body,
            link="/my-complaints", related_id=complaint.id,
        )


@router.post("/complaints", response_model=ComplaintRead, status_code=status.HTTP_201_CREATED)
def file_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.FARMER)),
):
    """File a complaint. Validates any linked request/machine/CHC, derives the
    effective CHC from a linked machine, and notifies the admins."""
    if current_user.farmer_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Your account is not linked to a farmer profile."
        )
    farmer_id = current_user.farmer_id

    # Validate optional links. A linked request must be the farmer's own.
    if payload.demand_request_id is not None:
        req = db.get(DemandRequest, payload.demand_request_id)
        if req is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Request {payload.demand_request_id} not found"
            )
        if req.farmer_id != farmer_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Request {payload.demand_request_id} does not belong to you.",
            )

    machine = None
    if payload.machine_id is not None:
        machine = db.get(Machine, payload.machine_id)
        if machine is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Machine {payload.machine_id} not found")

    chc_id = payload.chc_id
    if chc_id is not None:
        if db.get(CHC, chc_id) is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"CHC {chc_id} not found")
    elif machine is not None:
        # Derive the effective CHC from the linked machine so it lands in that
        # CHC's staff queue; general complaints keep chc_id NULL (admin-only).
        chc_id = machine.chc_id

    complaint = Complaint(
        farmer_id=farmer_id,
        category=payload.category,
        description=payload.description,
        demand_request_id=payload.demand_request_id,
        machine_id=payload.machine_id,
        chc_id=chc_id,
        status="open",
    )
    db.add(complaint)
    db.flush()  # assign id for the notification's related_id
    _notify_admins(
        db, complaint,
        title="New farmer complaint",
        body=f"A farmer filed a '{payload.category}' complaint.",
    )
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("/me/complaints", response_model=list[ComplaintRead])
def my_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.FARMER)),
):
    """The current farmer's own complaints, newest first."""
    if current_user.farmer_id is None:
        return []
    return db.scalars(
        select(Complaint)
        .where(Complaint.farmer_id == current_user.farmer_id)
        .order_by(Complaint.id.desc())
    ).all()


@router.get("/chc/{chc_id}/complaints", response_model=list[ComplaintRead])
def chc_complaints(
    chc_id: int,
    status_filter: ComplaintStatusLiteral | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_STAFF_ROLES)),
):
    """Complaints for one CHC. Role-gated (any manager/admin); the CHC id is an
    explicit filter, matching Phase 16's role-scoped model (no manager<->CHC link)."""
    stmt = select(Complaint).where(Complaint.chc_id == chc_id)
    if status_filter:
        stmt = stmt.where(Complaint.status == status_filter)
    return db.scalars(stmt.order_by(Complaint.id.desc())).all()


@router.get("/admin/complaints", response_model=list[ComplaintRead])
def all_complaints(
    status_filter: ComplaintStatusLiteral | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Every complaint (admin only), including general (chc_id NULL) ones."""
    stmt = select(Complaint)
    if status_filter:
        stmt = stmt.where(Complaint.status == status_filter)
    return db.scalars(stmt.order_by(Complaint.id.desc())).all()


def _get_or_404(db: Session, complaint_id: int) -> Complaint:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Complaint {complaint_id} not found")
    return complaint


@router.post("/complaints/{complaint_id}/respond", response_model=ComplaintRead)
def respond_complaint(
    complaint_id: int,
    payload: ComplaintRespondIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_STAFF_ROLES)),
):
    """Record a staff response; move open -> in_progress; notify the farmer."""
    complaint = _get_or_404(db, complaint_id)
    if complaint.status in ("resolved", "closed"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot respond to a '{complaint.status}' complaint.",
        )
    complaint.staff_response = payload.response
    complaint.responded_by_user_id = current_user.id
    if complaint.status == "open":
        complaint.status = "in_progress"
    db.flush()
    _notify_farmer(
        db, complaint,
        type=NotificationType.COMPLAINT_RESPONDED,
        title="Your complaint has a response",
        body="A staff member responded to your complaint.",
    )
    db.commit()
    db.refresh(complaint)
    return complaint


@router.post("/complaints/{complaint_id}/resolve", response_model=ComplaintRead)
def resolve_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_STAFF_ROLES)),
):
    """Mark a complaint resolved (from open / in_progress); notify the farmer."""
    complaint = _get_or_404(db, complaint_id)
    if complaint.status not in ("open", "in_progress"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot resolve a '{complaint.status}' complaint.",
        )
    complaint.status = "resolved"
    db.flush()
    _notify_farmer(
        db, complaint,
        type=NotificationType.COMPLAINT_RESOLVED,
        title="Your complaint was resolved",
        body="Your complaint has been marked resolved.",
    )
    db.commit()
    db.refresh(complaint)
    return complaint


@router.post("/complaints/{complaint_id}/close", response_model=ComplaintRead)
def close_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_STAFF_ROLES)),
):
    """Close a resolved complaint (terminal - no further action needed)."""
    complaint = _get_or_404(db, complaint_id)
    if complaint.status != "resolved":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only a resolved complaint can be closed (status is '{complaint.status}').",
        )
    complaint.status = "closed"
    db.commit()
    db.refresh(complaint)
    return complaint
