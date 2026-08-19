"""Phase 19 - complaints API tests: RBAC scoping, notifications, lifecycle."""
import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database import Base, get_db
import app.models  # noqa: F401
from app.main import app
from app.models import CHC, DemandRequest, Farmer, Field, Machine, Notification, User


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


def _headers(user):
    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    return {"Authorization": f"Bearer {token}"}


def _farmer(db, name):
    f = Farmer(name=name, phone="9999999999", village="V", latitude=20.0, longitude=77.0)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def _user(db, email, role, farmer_id=None):
    u = User(name=email, email=email, password_hash="x", role=role, is_active=True, farmer_id=farmer_id)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _chc(db, name):
    c = CHC(name=name, location="L", latitude=20.0, longitude=77.0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _machine(db, chc_id, mtype="Combine Harvester"):
    m = Machine(chc_id=chc_id, machine_type=mtype, current_latitude=20.0, current_longitude=77.0)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _request(db, farmer_id):
    fld = Field(farmer_id=farmer_id, crop_type="Wheat", latitude=20.0, longitude=77.0)
    db.add(fld)
    db.commit()
    db.refresh(fld)
    req = DemandRequest(
        farmer_id=farmer_id, field_id=fld.id, operation_type="Harvesting",
        requested_date=dt.date.today(), urgency="medium", status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def _file(client, user, **body):
    body.setdefault("category", "other")
    body.setdefault("description", "something went wrong")
    return client.post("/api/complaints", headers=_headers(user), json=body)


def test_farmer_sees_only_own_complaints(client, db_session):
    fa, fb = _farmer(db_session, "A"), _farmer(db_session, "B")
    ua = _user(db_session, "a@t.com", "FARMER", farmer_id=fa.id)
    ub = _user(db_session, "b@t.com", "FARMER", farmer_id=fb.id)

    assert _file(client, ua, description="A problem").status_code == 201
    assert _file(client, ub, description="B problem").status_code == 201

    mine = client.get("/api/me/complaints", headers=_headers(ua))
    assert mine.status_code == 200
    data = mine.json()
    assert len(data) == 1
    assert data[0]["description"] == "A problem"
    assert data[0]["farmer_id"] == fa.id


def test_chc_scoped_list_and_chc_derived_from_machine(client, db_session):
    fa = _farmer(db_session, "A")
    ua = _user(db_session, "a@t.com", "FARMER", farmer_id=fa.id)
    admin = _user(db_session, "admin@t.com", "ADMIN")
    chc1, chc2 = _chc(db_session, "CHC1"), _chc(db_session, "CHC2")
    m1 = _machine(db_session, chc1.id)

    # A machine-linked complaint derives chc_id from the machine.
    r1 = _file(client, ua, category="machine_breakdown", description="broke", machine_id=m1.id)
    assert r1.status_code == 201
    assert r1.json()["chc_id"] == chc1.id

    # A general complaint has no CHC.
    _file(client, ua, description="general issue")

    c1 = client.get(f"/api/chc/{chc1.id}/complaints", headers=_headers(admin))
    assert c1.status_code == 200 and len(c1.json()) == 1 and c1.json()[0]["machine_id"] == m1.id

    c2 = client.get(f"/api/chc/{chc2.id}/complaints", headers=_headers(admin))
    assert c2.json() == []

    all_ = client.get("/api/admin/complaints", headers=_headers(admin))
    assert len(all_.json()) == 2  # includes the general one


def test_admin_endpoint_forbidden_for_manager_but_chc_allowed(client, db_session):
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    chc = _chc(db_session, "CHC1")
    assert client.get("/api/admin/complaints", headers=_headers(mgr)).status_code == 403
    assert client.get(f"/api/chc/{chc.id}/complaints", headers=_headers(mgr)).status_code == 200


def test_filing_notifies_all_admins(client, db_session):
    fa = _farmer(db_session, "A")
    ua = _user(db_session, "a@t.com", "FARMER", farmer_id=fa.id)
    admin1 = _user(db_session, "admin1@t.com", "ADMIN")
    admin2 = _user(db_session, "admin2@t.com", "ADMIN")

    cid = _file(client, ua).json()["id"]

    notes = db_session.scalars(
        select(Notification).where(Notification.type == "complaint_filed")
    ).all()
    assert {n.user_id for n in notes} == {admin1.id, admin2.id}
    assert all(n.related_id == cid for n in notes)


def test_respond_transitions_open_to_in_progress_and_notifies_farmer(client, db_session):
    fa = _farmer(db_session, "A")
    ua = _user(db_session, "a@t.com", "FARMER", farmer_id=fa.id)
    admin = _user(db_session, "admin@t.com", "ADMIN")
    cid = _file(client, ua).json()["id"]

    r = client.post(
        f"/api/complaints/{cid}/respond",
        headers=_headers(admin),
        json={"response": "We are looking into it."},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "in_progress"
    assert body["staff_response"] == "We are looking into it."
    assert body["responded_by_user_id"] == admin.id

    fnotes = db_session.scalars(
        select(Notification).where(
            Notification.user_id == ua.id, Notification.type == "complaint_responded"
        )
    ).all()
    assert len(fnotes) == 1 and fnotes[0].related_id == cid


def test_farmer_cannot_respond_to_own_complaint(client, db_session):
    fa = _farmer(db_session, "A")
    ua = _user(db_session, "a@t.com", "FARMER", farmer_id=fa.id)
    cid = _file(client, ua).json()["id"]

    r = client.post(
        f"/api/complaints/{cid}/respond", headers=_headers(ua), json={"response": "me"}
    )
    assert r.status_code == 403  # role check, not ownership


def test_manager_cannot_file_complaint(client, db_session):
    mgr = _user(db_session, "m@t.com", "CHC_MANAGER")
    r = client.post(
        "/api/complaints", headers=_headers(mgr), json={"category": "other", "description": "x"}
    )
    assert r.status_code == 403


def test_full_lifecycle_resolve_then_close(client, db_session):
    fa = _farmer(db_session, "A")
    ua = _user(db_session, "a@t.com", "FARMER", farmer_id=fa.id)
    admin = _user(db_session, "admin@t.com", "ADMIN")
    cid = _file(client, ua).json()["id"]

    r = client.post(f"/api/complaints/{cid}/resolve", headers=_headers(admin))
    assert r.status_code == 200 and r.json()["status"] == "resolved"
    assert db_session.scalars(
        select(Notification).where(
            Notification.user_id == ua.id, Notification.type == "complaint_resolved"
        )
    ).all()

    r2 = client.post(f"/api/complaints/{cid}/close", headers=_headers(admin))
    assert r2.status_code == 200 and r2.json()["status"] == "closed"

    # A closed complaint can't be resolved again.
    assert client.post(f"/api/complaints/{cid}/resolve", headers=_headers(admin)).status_code == 409


def test_close_requires_resolved(client, db_session):
    fa = _farmer(db_session, "A")
    ua = _user(db_session, "a@t.com", "FARMER", farmer_id=fa.id)
    admin = _user(db_session, "admin@t.com", "ADMIN")
    cid = _file(client, ua).json()["id"]
    # Still open -> cannot close.
    assert client.post(f"/api/complaints/{cid}/close", headers=_headers(admin)).status_code == 409


def test_cannot_link_another_farmers_request(client, db_session):
    fa, fb = _farmer(db_session, "A"), _farmer(db_session, "B")
    ua = _user(db_session, "a@t.com", "FARMER", farmer_id=fa.id)
    req_b = _request(db_session, fb.id)
    r = _file(client, ua, demand_request_id=req_b.id)
    assert r.status_code == 400
