"""Phase 20 (Part A) - end-to-end integration test.

Chains the REAL, unmodified endpoints from Phases 16 + 19 through one farmer
journey against a single shared in-memory DB session (no internal mocks - the
real allocation engine picks the machine):

    create request -> assign via recommendation -> file complaint
                    -> respond -> resolve

then reads the farmer's own notifications via the real notifications endpoint and
asserts their chronological order.

NOTE on step 2: request creation notifies the ADMINs. `create_request` fans out
a `request_created` notification to all admins (Phase 20 fix, mirroring
`complaint_filed` - there is no manager<->CHC link, so admins are the reliable
staff recipient). The farmer is not self-notified, so the farmer's own
notification sequence still begins with `request_assigned`.
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


@pytest.fixture
def db_session():
    # StaticPool -> the test and the app share ONE in-memory connection, so the
    # rows this test seeds are the same rows the endpoints read/write.
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


def _auth(user):
    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    return {"Authorization": f"Bearer {token}"}


def test_full_connected_loop(client, db_session):
    today = date.today()

    # --- Minimum REAL data the allocation engine needs to return a candidate:
    # two CHCs (-> two clusters), one operational combine positioned near the
    # field with availability in the forecast window, one incompatible tractor.
    north = CHC(name="North", location="N", latitude=27.0, longitude=80.0)
    south = CHC(name="South", location="S", latitude=26.6, longitude=80.3)
    db_session.add_all([north, south])
    db_session.flush()
    combine = Machine(
        chc_id=north.id, machine_type="Combine Harvester", capacity=4.0,
        operating_radius=100.0, maintenance_status="operational",
        current_latitude=26.62, current_longitude=80.31,
    )
    tractor = Machine(
        chc_id=south.id, machine_type="Tractor", capacity=3.0,
        operating_radius=80.0, maintenance_status="operational",
        current_latitude=26.60, current_longitude=80.30,
    )
    db_session.add_all([combine, tractor])
    db_session.flush()
    for d in range(3):
        db_session.add(MachineAvailability(
            machine_id=combine.id, date=today + timedelta(days=d),
            start_time=time(8, 0), end_time=time(18, 0), status="available",
        ))

    farmer = Farmer(
        name="Farmer A", phone="9990000000", village="Southville",
        latitude=26.60, longitude=80.30,
    )
    db_session.add(farmer)
    db_session.flush()
    field = Field(
        farmer_id=farmer.id, crop_type="Wheat", area=3.0, latitude=26.60, longitude=80.30
    )
    db_session.add(field)
    db_session.flush()

    # Logins: the farmer (linked to the profile) + an admin (complaint recipient
    # and the staff actor who assigns/responds/resolves).
    farmer_user = User(
        name="fa", email="fa@t.com", password_hash="x", role="FARMER",
        is_active=True, farmer_id=farmer.id,
    )
    admin_user = User(name="ad", email="ad@t.com", password_hash="x", role="ADMIN", is_active=True)
    db_session.add_all([farmer_user, admin_user])
    db_session.commit()
    db_session.refresh(farmer_user)
    db_session.refresh(admin_user)

    fa_auth = _auth(farmer_user)
    ad_auth = _auth(admin_user)

    # === 1. Farmer creates a request via the real endpoint ===
    r = client.post(
        "/api/requests",
        headers=fa_auth,
        json={
            "farmer_id": farmer.id,  # ignored for FARMER (own profile); schema requires it
            "field_id": field.id,
            "operation_type": "Harvesting",
            "requested_date": str(today + timedelta(days=2)),
            "urgency": "high",
        },
    )
    assert r.status_code == 201, r.text
    request_id = r.json()["id"]
    assert r.json()["status"] == "pending"

    # === 2. Request creation notifies the ADMINs (not the farmer) ===
    assert client.get("/api/me/notifications", headers=fa_auth).json() == []
    admin_notes = client.get("/api/me/notifications", headers=ad_auth).json()
    assert [n["type"] for n in admin_notes] == ["request_created"]
    assert admin_notes[0]["related_id"] == request_id

    # === 3. Assign via the REAL recommendation engine (not a mock) ===
    r = client.post(
        f"/api/requests/{request_id}/assign", headers=ad_auth, json={"use_recommendation": True}
    )
    assert r.status_code == 200, r.text
    assert r.json()["machine_id"] == combine.id  # the engine's compatible, available pick

    # === 4. allocated + a real Booking row + farmer notified request_assigned ===
    assert db_session.get(DemandRequest, request_id).status == "allocated"
    booking = db_session.scalar(select(Booking).where(Booking.demand_request_id == request_id))
    assert booking is not None and booking.machine_id == combine.id and booking.status == "active"
    assigned = db_session.scalars(
        select(Notification).where(
            Notification.user_id == farmer_user.id, Notification.type == "request_assigned"
        )
    ).all()
    assert len(assigned) == 1

    # === 5. Farmer files a complaint linked to that request + the assigned machine ===
    r = client.post(
        "/api/complaints",
        headers=fa_auth,
        json={
            "category": "machine_breakdown",
            "description": "The assigned combine broke down on arrival.",
            "demand_request_id": request_id,
            "machine_id": combine.id,
        },
    )
    assert r.status_code == 201, r.text
    complaint_id = r.json()["id"]
    assert r.json()["chc_id"] == combine.chc_id  # derived from the linked machine

    # === 6. Admin got complaint_filed ===
    filed = db_session.scalars(
        select(Notification).where(
            Notification.user_id == admin_user.id,
            Notification.type == "complaint_filed",
            Notification.related_id == complaint_id,
        )
    ).all()
    assert len(filed) == 1

    # === 7. Admin responds -> in_progress + farmer notified ===
    r = client.post(
        f"/api/complaints/{complaint_id}/respond",
        headers=ad_auth,
        json={"response": "A replacement machine is on the way."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "in_progress"

    # === 8. Admin resolves -> resolved + farmer notified ===
    r = client.post(f"/api/complaints/{complaint_id}/resolve", headers=ad_auth)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "resolved"

    # === 9. The farmer's own notifications, read via the real endpoint, in
    # chronological order. The endpoint returns newest-first, so reverse it. ===
    notes = client.get("/api/me/notifications", headers=fa_auth).json()
    types_chrono = [n["type"] for n in reversed(notes)]
    assert types_chrono == ["request_assigned", "complaint_responded", "complaint_resolved"]
