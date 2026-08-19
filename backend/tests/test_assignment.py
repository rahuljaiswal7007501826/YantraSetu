"""Phase 16 - real assignment workflow tests.

Same TestClient + in-memory StaticPool + get_db override pattern as the other
suites (real DB never touched). Covers direct assign, assign-via-recommendation
(which must call the real allocation engine), reject-with-reason + notification,
cancel + booking void + ownership, status guards, and role gating. No cross-CHC
test - per the Option B decision there is no manager-CHC link.
"""
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database import Base, get_db
import app.models  # noqa: F401
from app.main import app
from app.models import (
    CHC,
    Booking,
    DemandRequest,
    Farmer,
    Field,
    Machine,
    MachineAvailability,
    Notification,
    User,
)
from app.services.allocation_engine import recommend_machines


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = Session()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _user(db, email, role, farmer_id=None):
    u = User(name=email.split("@")[0], email=email, password_hash="x", role=role,
             is_active=True, farmer_id=farmer_id)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _auth(user):
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id, role=user.role, email=user.email)}"}


@pytest.fixture
def world(db_session):
    """A combine (compatible + available) and a tractor (incompatible with
    Harvesting), plus two farmers each with a pending Harvesting request."""
    today = date.today()
    north = CHC(name="North", location="N", latitude=27.0, longitude=80.0)
    south = CHC(name="South", location="S", latitude=26.6, longitude=80.3)
    db_session.add_all([north, south])
    db_session.flush()
    combine = Machine(chc_id=north.id, machine_type="Combine Harvester", capacity=4.0,
                      operating_radius=100.0, maintenance_status="operational",
                      current_latitude=26.62, current_longitude=80.31)
    tractor = Machine(chc_id=south.id, machine_type="Tractor", capacity=3.0,
                      operating_radius=80.0, maintenance_status="operational",
                      current_latitude=26.60, current_longitude=80.30)
    db_session.add_all([combine, tractor])
    db_session.flush()
    for d in range(3):
        day = today + timedelta(days=d)
        db_session.add(MachineAvailability(machine_id=combine.id, date=day, start_time=time(8, 0),
                                           end_time=time(18, 0), status="available"))
    out = {"combine": combine, "tractor": tractor}
    for key, (lat, lon) in (("A", (26.60, 80.30)), ("B", (26.70, 80.40))):
        f = Farmer(name=f"Farmer {key}", phone="9990000000", village="V" + key, latitude=lat, longitude=lon)
        db_session.add(f)
        db_session.flush()
        fld = Field(farmer_id=f.id, crop_type="Wheat", area=3.0, latitude=lat, longitude=lon)
        db_session.add(fld)
        db_session.flush()
        r = DemandRequest(farmer_id=f.id, field_id=fld.id, operation_type="Harvesting",
                          requested_date=today + timedelta(days=2), urgency="high", status="pending")
        db_session.add(r)
        db_session.flush()
        out[f"farmer{key}"], out[f"field{key}"], out[f"req{key}"] = f, fld, r
    db_session.commit()
    return out


def _booking(db, request_id):
    return db.scalar(select(Booking).where(Booking.demand_request_id == request_id))


# --------------------------------------------------------------------------- #
# assign - direct
# --------------------------------------------------------------------------- #
def test_assign_direct_creates_booking_and_allocates(client, db_session, world):
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    rid, mid = world["reqA"].id, world["combine"].id
    r = client.post(f"/api/requests/{rid}/assign", headers=_auth(mgr), json={"machine_id": mid})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["machine_id"] == mid and body["demand_request_id"] == rid and body["status"] == "active"

    assert db_session.get(DemandRequest, rid).status == "allocated"
    bk = _booking(db_session, rid)
    assert bk is not None and bk.machine_id == mid and bk.assigned_by_user_id == mgr.id


def test_assign_incompatible_machine_400(client, db_session, world):
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    # Tractor cannot perform Harvesting -> hard compatibility gate.
    r = client.post(f"/api/requests/{world['reqA'].id}/assign",
                    headers=_auth(mgr), json={"machine_id": world["tractor"].id})
    assert r.status_code == 400


def test_assign_unknown_machine_400(client, db_session, world):
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    r = client.post(f"/api/requests/{world['reqA'].id}/assign",
                    headers=_auth(mgr), json={"machine_id": 999999})
    assert r.status_code == 400


def test_reassign_updates_same_booking(client, db_session, world):
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    rid, mid = world["reqA"].id, world["combine"].id
    client.post(f"/api/requests/{rid}/assign", headers=_auth(mgr), json={"machine_id": mid})
    client.post(f"/api/requests/{rid}/assign", headers=_auth(mgr), json={"machine_id": mid})
    bookings = db_session.scalars(select(Booking).where(Booking.demand_request_id == rid)).all()
    assert len(bookings) == 1  # unique per request -> re-assign updates in place


# --------------------------------------------------------------------------- #
# assign - via recommendation (must use the real engine)
# --------------------------------------------------------------------------- #
def test_assign_via_recommendation_uses_real_engine(client, db_session, world):
    rid = world["reqA"].id
    expected = recommend_machines(db_session, rid, top_n=1)  # the real engine
    assert expected, "engine should find the compatible, available combine"
    expected_machine_id = expected[0].machine_id

    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    r = client.post(f"/api/requests/{rid}/assign", headers=_auth(mgr), json={"use_recommendation": True})
    assert r.status_code == 200, r.text
    assert r.json()["machine_id"] == expected_machine_id  # assigned the engine's top pick
    assert db_session.get(DemandRequest, rid).status == "allocated"


# --------------------------------------------------------------------------- #
# reject
# --------------------------------------------------------------------------- #
def test_reject_requires_reason(client, db_session, world):
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    assert client.post(f"/api/requests/{world['reqA'].id}/reject", headers=_auth(mgr), json={}).status_code == 422


def test_reject_sets_status_and_notifies_farmer(client, db_session, world):
    _user(db_session, "farmerA@t.com", "FARMER", farmer_id=world["farmerA"].id)  # linked farmer login
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    rid = world["reqA"].id
    r = client.post(f"/api/requests/{rid}/reject", headers=_auth(mgr),
                    json={"reason": "No combine available this week"})
    assert r.status_code == 200 and r.json()["status"] == "rejected"

    fa = db_session.scalar(select(User).where(User.email == "farmerA@t.com"))
    notes = db_session.scalars(
        select(Notification).where(Notification.user_id == fa.id, Notification.type == "request_rejected")
    ).all()
    assert len(notes) == 1
    assert "No combine available this week" in notes[0].body


def test_reject_non_pending_409(client, db_session, world):
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    rid = world["reqA"].id
    client.post(f"/api/requests/{rid}/assign", headers=_auth(mgr), json={"machine_id": world["combine"].id})
    # now allocated -> cannot reject
    r = client.post(f"/api/requests/{rid}/reject", headers=_auth(mgr), json={"reason": "late"})
    assert r.status_code == 409


# --------------------------------------------------------------------------- #
# assign notifies the farmer
# --------------------------------------------------------------------------- #
def test_assign_notifies_linked_farmer(client, db_session, world):
    _user(db_session, "farmerA@t.com", "FARMER", farmer_id=world["farmerA"].id)
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    client.post(f"/api/requests/{world['reqA'].id}/assign", headers=_auth(mgr),
                json={"machine_id": world["combine"].id})
    fa = db_session.scalar(select(User).where(User.email == "farmerA@t.com"))
    notes = db_session.scalars(
        select(Notification).where(Notification.user_id == fa.id, Notification.type == "request_assigned")
    ).all()
    assert len(notes) == 1


# --------------------------------------------------------------------------- #
# cancel
# --------------------------------------------------------------------------- #
def test_cancel_voids_booking(client, db_session, world):
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    rid = world["reqA"].id
    client.post(f"/api/requests/{rid}/assign", headers=_auth(mgr), json={"machine_id": world["combine"].id})
    r = client.post(f"/api/requests/{rid}/cancel", headers=_auth(mgr))
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert _booking(db_session, rid).status == "voided"


def test_farmer_cancels_own_request(client, db_session, world):
    fa = _user(db_session, "farmerA@t.com", "FARMER", farmer_id=world["farmerA"].id)
    r = client.post(f"/api/requests/{world['reqA'].id}/cancel", headers=_auth(fa))
    assert r.status_code == 200 and r.json()["status"] == "cancelled"


def test_farmer_cannot_cancel_another_farmers_request(client, db_session, world):
    fa = _user(db_session, "farmerA@t.com", "FARMER", farmer_id=world["farmerA"].id)
    # reqB belongs to farmer B -> 404 (owner-scoped, no enumeration)
    assert client.post(f"/api/requests/{world['reqB'].id}/cancel", headers=_auth(fa)).status_code == 404


# --------------------------------------------------------------------------- #
# role gating
# --------------------------------------------------------------------------- #
def test_assign_and_reject_forbidden_for_farmer(client, db_session, world):
    fa = _user(db_session, "farmerA@t.com", "FARMER", farmer_id=world["farmerA"].id)
    rid = world["reqA"].id
    assert client.post(f"/api/requests/{rid}/assign", headers=_auth(fa),
                       json={"machine_id": world["combine"].id}).status_code == 403
    assert client.post(f"/api/requests/{rid}/reject", headers=_auth(fa),
                       json={"reason": "x"}).status_code == 403


def test_assign_unauthenticated_401(client, db_session, world):
    assert client.post(f"/api/requests/{world['reqA'].id}/assign",
                       json={"machine_id": world["combine"].id}).status_code == 401
