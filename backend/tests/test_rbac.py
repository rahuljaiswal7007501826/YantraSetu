"""RBAC endpoint tests (Step I).

These exercise the real HTTP layer via TestClient so the router-level and
endpoint-level role guards are actually evaluated. A dedicated in-memory SQLite
engine with StaticPool is used so the TestClient worker thread shares the same
database as the test. The real project database is never touched (get_db is
overridden and the app lifespan is not run - TestClient is used without `with`).
"""
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database import Base, get_db
import app.models  # noqa: F401 - registers all tables on Base.metadata
from app.main import app
from app.models import (
    CHC,
    DemandRequest,
    Farmer,
    Field,
    Machine,
    MachineAvailability,
    User,
)

ROLES = ("ADMIN", "CHC_MANAGER", "OPERATOR", "FARMER")


@pytest.fixture
def db_session():
    # StaticPool -> every connection (incl. the TestClient worker thread) shares
    # the SAME in-memory database, so seeded rows are visible to request handlers.
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
    yield TestClient(app)  # no `with`: the lifespan (init_db) never runs
    app.dependency_overrides.clear()


def _auth(user: User) -> dict:
    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers(db_session):
    """One user per role; returns {role: Authorization header}."""
    for role in ROLES:
        db_session.add(
            User(name=role, email=f"{role.lower()}@t.com", password_hash="x",
                 role=role, is_active=True)
        )
    db_session.commit()
    out = {}
    for role in ROLES:
        u = db_session.query(User).filter_by(email=f"{role.lower()}@t.com").one()
        out[role] = _auth(u)
    return out


def _seed_world(s):
    """Minimal but complete dataset so engine-backed endpoints return 200."""
    today = date.today()
    north = CHC(name="North", location="N", latitude=27.0, longitude=80.0)
    south = CHC(name="South", location="S", latitude=26.6, longitude=80.3)
    s.add_all([north, south])
    s.flush()
    combine = Machine(chc_id=north.id, machine_type="Combine Harvester", capacity=4.0,
                      operating_radius=100.0, maintenance_status="operational",
                      current_latitude=27.0, current_longitude=80.0)
    tractor = Machine(chc_id=south.id, machine_type="Tractor", capacity=3.0,
                      operating_radius=80.0, maintenance_status="operational",
                      current_latitude=26.6, current_longitude=80.3)
    s.add_all([combine, tractor])
    s.flush()
    for d in range(3):
        day = today + timedelta(days=d)
        s.add(MachineAvailability(machine_id=combine.id, date=day, start_time=time(8, 0),
                                  end_time=time(18, 0), status="available"))
        s.add(MachineAvailability(machine_id=tractor.id, date=day, start_time=time(8, 0),
                                  end_time=time(18, 0), status="booked"))
    out = {"chcNorth": north, "chcSouth": south, "combine": combine, "tractor": tractor}
    for key, (lat, lon) in (("A", (26.60, 80.30)), ("B", (26.70, 80.40))):
        f = Farmer(name=f"Farmer {key}", phone="9990000000", village="V" + key, latitude=lat, longitude=lon)
        s.add(f)
        s.flush()
        fld = Field(farmer_id=f.id, crop_type="Wheat", area=3.0, latitude=lat, longitude=lon)
        s.add(fld)
        s.flush()
        r = DemandRequest(farmer_id=f.id, field_id=fld.id, operation_type="Harvesting",
                          requested_date=today + timedelta(days=2), urgency="high", status="pending")
        s.add(r)
        s.flush()
        out[f"farmer{key}"] = f
        out[f"field{key}"] = fld
        out[f"req{key}"] = r
    s.commit()
    return out


@pytest.fixture
def world(db_session):
    return _seed_world(db_session)


# --------------------------------------------------------------------------- #
# 1. Unauthenticated -> 401
# --------------------------------------------------------------------------- #
PROTECTED_GET = [
    "/api/machines", "/api/chcs", "/api/forecast", "/api/forecast/shortages",
    "/api/analytics/summary", "/api/analytics/utilization", "/api/analytics/impact",
    "/api/dashboard/admin", "/api/map/machines", "/api/map/shortages",
    "/api/relocations", "/api/requests", "/api/farmers", "/api/fields",
]


@pytest.mark.parametrize("path", PROTECTED_GET)
def test_unauthenticated_returns_401(client, path):
    assert client.get(path).status_code == 401


# --------------------------------------------------------------------------- #
# 2. Authenticated but wrong role -> 403
# --------------------------------------------------------------------------- #
FORBIDDEN = [
    ("FARMER", "/api/machines"), ("FARMER", "/api/chcs"), ("FARMER", "/api/forecast"),
    ("FARMER", "/api/analytics/summary"), ("FARMER", "/api/dashboard/admin"),
    ("FARMER", "/api/relocations"), ("FARMER", "/api/farmers"), ("FARMER", "/api/fields"),
    ("OPERATOR", "/api/forecast"), ("OPERATOR", "/api/analytics/summary"),
    ("OPERATOR", "/api/dashboard/admin"), ("OPERATOR", "/api/relocations"),
    ("OPERATOR", "/api/requests"), ("OPERATOR", "/api/farmers"), ("OPERATOR", "/api/fields"),
    ("CHC_MANAGER", "/api/analytics/summary"), ("CHC_MANAGER", "/api/dashboard/admin"),
]


@pytest.mark.parametrize("role,path", FORBIDDEN)
def test_wrong_role_returns_403(client, headers, role, path):
    assert client.get(path, headers=headers[role]).status_code == 403


# --------------------------------------------------------------------------- #
# 3. Correct role -> 200 (guard passes, existing behavior preserved)
# --------------------------------------------------------------------------- #
ALLOWED = [
    ("ADMIN", "/api/machines"), ("ADMIN", "/api/forecast"), ("ADMIN", "/api/analytics/summary"),
    ("ADMIN", "/api/dashboard/admin"), ("ADMIN", "/api/relocations"), ("ADMIN", "/api/farmers"),
    ("ADMIN", "/api/fields"), ("ADMIN", "/api/map/machines"), ("ADMIN", "/api/requests"),
    ("CHC_MANAGER", "/api/machines"), ("CHC_MANAGER", "/api/chcs"), ("CHC_MANAGER", "/api/forecast"),
    ("CHC_MANAGER", "/api/relocations"), ("CHC_MANAGER", "/api/farmers"), ("CHC_MANAGER", "/api/requests"),
    ("OPERATOR", "/api/machines"), ("OPERATOR", "/api/chcs"), ("OPERATOR", "/api/map/machines"),
    ("OPERATOR", "/api/map/shortages"),
    ("FARMER", "/api/map/machines"),
]


@pytest.mark.parametrize("role,path", ALLOWED)
def test_correct_role_allowed(client, headers, world, role, path):
    r = client.get(path, headers=headers[role])
    assert r.status_code == 200, r.text


# --------------------------------------------------------------------------- #
# 4. /api/demo/* stays OPEN (no auth needed)
# --------------------------------------------------------------------------- #
def test_demo_reset_open_without_auth(client):
    assert client.post("/api/demo/reset").status_code == 200


# --------------------------------------------------------------------------- #
# 5. FARMER request ownership (enforced at the query level)
# --------------------------------------------------------------------------- #
def _farmer_user(db_session, farmer_id):
    u = User(name="Linked Farmer", email="linked@t.com", password_hash="x",
             role="FARMER", is_active=True, farmer_id=farmer_id)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def test_farmer_lists_only_own_requests(client, db_session, world):
    fu = _farmer_user(db_session, world["farmerA"].id)
    r = client.get("/api/requests", headers=_auth(fu))
    assert r.status_code == 200
    ids = {row["id"] for row in r.json()}
    assert world["reqA"].id in ids
    assert world["reqB"].id not in ids


def test_farmer_cannot_get_another_farmers_request(client, db_session, world):
    fu = _farmer_user(db_session, world["farmerA"].id)
    assert client.get(f"/api/requests/{world['reqB'].id}", headers=_auth(fu)).status_code == 404
    assert client.get(f"/api/requests/{world['reqA'].id}", headers=_auth(fu)).status_code == 200


def test_admin_sees_all_requests(client, headers, world):
    r = client.get("/api/requests", headers=headers["ADMIN"])
    assert r.status_code == 200
    ids = {row["id"] for row in r.json()}
    assert world["reqA"].id in ids and world["reqB"].id in ids


def test_farmer_create_is_forced_to_own_farmer_id(client, db_session, world):
    fu = _farmer_user(db_session, world["farmerA"].id)
    # Try to create against farmer B in the payload, but on farmer A's own field.
    payload = {
        "farmer_id": world["farmerB"].id,       # should be ignored for a FARMER
        "field_id": world["fieldA"].id,
        "operation_type": "Harvesting",
        "requested_date": str(date.today()),
        "urgency": "high",
    }
    r = client.post("/api/requests", headers=_auth(fu), json=payload)
    assert r.status_code == 201, r.text
    assert r.json()["farmer_id"] == world["farmerA"].id  # forced to their own profile


def test_create_request_notifies_admins(client, db_session, world, headers):
    """A new request fans out a request_created notification to every ADMIN; the
    farmer who filed it is not self-notified."""
    fu = _farmer_user(db_session, world["farmerA"].id)
    payload = {
        "farmer_id": world["farmerA"].id,
        "field_id": world["fieldA"].id,
        "operation_type": "Harvesting",
        "requested_date": str(date.today()),
        "urgency": "high",
    }
    r = client.post("/api/requests", headers=_auth(fu), json=payload)
    assert r.status_code == 201, r.text
    request_id = r.json()["id"]

    admin_notes = client.get("/api/me/notifications", headers=headers["ADMIN"]).json()
    created = [n for n in admin_notes if n["type"] == "request_created"]
    assert len(created) == 1 and created[0]["related_id"] == request_id
    # The farmer who filed it is not self-notified.
    assert client.get("/api/me/notifications", headers=_auth(fu)).json() == []


def test_farmer_without_profile_link_cannot_create(client, db_session, world):
    fu = _farmer_user(db_session, None)  # not linked to any Farmer
    payload = {
        "farmer_id": world["farmerA"].id,
        "field_id": world["fieldA"].id,
        "operation_type": "Harvesting",
        "requested_date": str(date.today()),
        "urgency": "high",
    }
    assert client.post("/api/requests", headers=_auth(fu), json=payload).status_code == 400


def test_farmer_without_profile_link_sees_empty_requests(client, db_session, world):
    fu = _farmer_user(db_session, None)
    r = client.get("/api/requests", headers=_auth(fu))
    assert r.status_code == 200
    assert r.json() == []


# --------------------------------------------------------------------------- #
# 6. Phase I-B: write / decision endpoints
# --------------------------------------------------------------------------- #
def _machine_payload(world):
    return {
        "chc_id": world["chcNorth"].id,
        "machine_type": "Tractor",
        "capacity": 3.0,
        "operating_radius": 50.0,
        "maintenance_status": "operational",
        "current_latitude": 27.0,
        "current_longitude": 80.0,
    }


_CHC_PAYLOAD = {
    "name": "New CHC",
    "location": "Somewhere",
    "latitude": 26.9,
    "longitude": 80.5,
    "operating_hours": "09:00-18:00",
}


# --- machine writes: operators + farmers blocked, managers/admins allowed ---
def test_machine_create_unauthenticated_401(client, world):
    assert client.post("/api/machines", json=_machine_payload(world)).status_code == 401


@pytest.mark.parametrize("role", ["FARMER", "OPERATOR"])
def test_machine_create_forbidden_for_non_managers(client, headers, world, role):
    assert client.post("/api/machines", headers=headers[role], json=_machine_payload(world)).status_code == 403


@pytest.mark.parametrize("role", ["CHC_MANAGER", "ADMIN"])
def test_machine_create_allowed_for_managers(client, headers, world, role):
    r = client.post("/api/machines", headers=headers[role], json=_machine_payload(world))
    assert r.status_code == 201, r.text


def test_operator_can_read_but_not_delete_machine(client, headers, world):
    mid = world["combine"].id
    assert client.get(f"/api/machines/{mid}", headers=headers["OPERATOR"]).status_code == 200
    assert client.delete(f"/api/machines/{mid}", headers=headers["OPERATOR"]).status_code == 403


def test_manager_can_update_machine(client, headers, world):
    r = client.put(f"/api/machines/{world['combine'].id}", headers=headers["CHC_MANAGER"],
                   json={"capacity": 5.5})
    assert r.status_code == 200, r.text


# --- chc writes ---
@pytest.mark.parametrize("role", ["FARMER", "OPERATOR"])
def test_chc_create_forbidden_for_non_managers(client, headers, role):
    assert client.post("/api/chcs", headers=headers[role], json=_CHC_PAYLOAD).status_code == 403


def test_chc_create_allowed_for_manager(client, headers):
    assert client.post("/api/chcs", headers=headers["CHC_MANAGER"], json=_CHC_PAYLOAD).status_code == 201


# --- allocation recommend: managers + admins only ---
def test_allocation_unauthenticated_401(client, world):
    assert client.post("/api/allocation/recommend", json={"request_id": world["reqA"].id}).status_code == 401


@pytest.mark.parametrize("role", ["FARMER", "OPERATOR"])
def test_allocation_forbidden_for_non_managers(client, headers, world, role):
    body = {"request_id": world["reqA"].id}
    assert client.post("/api/allocation/recommend", headers=headers[role], json=body).status_code == 403


def test_allocation_allowed_for_manager(client, headers, world):
    r = client.post("/api/allocation/recommend", headers=headers["CHC_MANAGER"],
                    json={"request_id": world["reqA"].id})
    assert r.status_code == 200, r.text


# --- route optimize: operators + managers + admins ---
def test_routes_optimize_unauthenticated_401(client, world):
    body = {"machine_id": world["combine"].id, "request_ids": [world["reqA"].id]}
    assert client.post("/api/routes/optimize", json=body).status_code == 401


def test_routes_optimize_forbidden_for_farmer(client, headers, world):
    body = {"machine_id": world["combine"].id, "request_ids": [world["reqA"].id]}
    assert client.post("/api/routes/optimize", headers=headers["FARMER"], json=body).status_code == 403


@pytest.mark.parametrize("role", ["OPERATOR", "CHC_MANAGER", "ADMIN"])
def test_routes_optimize_allowed_for_operational_roles(client, headers, world, role):
    body = {"machine_id": world["combine"].id, "request_ids": [world["reqA"].id]}
    r = client.post("/api/routes/optimize", headers=headers[role], json=body)
    assert r.status_code == 201, r.text


# --- relocation approve/reject: managers + admins only (human decision gate) ---
def test_relocation_generate_unauthenticated_401(client):
    assert client.post("/api/relocations/generate").status_code == 401


def test_relocation_approve_forbidden_for_farmer(client, headers):
    assert client.post("/api/relocations/1/approve", headers=headers["FARMER"]).status_code == 403


def test_relocation_approve_manager_passes_guard(client, headers):
    # No such recommendation -> 404 (NOT 401/403), proving the guard let the manager in.
    assert client.post("/api/relocations/999/approve", headers=headers["CHC_MANAGER"]).status_code == 404


# --------------------------------------------------------------------------- #
# 7. Farmer self-service (/api/me) - owner-scoped, FARMER only
# --------------------------------------------------------------------------- #
def test_me_fields_unauthenticated_401(client, world):
    assert client.get("/api/me/fields").status_code == 401


def test_me_assignment_unauthenticated_401(client, world):
    assert client.get(f"/api/me/requests/{world['reqA'].id}/assignment").status_code == 401


@pytest.mark.parametrize("role", ["ADMIN", "CHC_MANAGER", "OPERATOR"])
def test_me_endpoints_forbidden_for_non_farmers(client, headers, world, role):
    assert client.get("/api/me/fields", headers=headers[role]).status_code == 403
    assert (
        client.get(f"/api/me/requests/{world['reqA'].id}/assignment", headers=headers[role]).status_code
        == 403
    )


def test_farmer_sees_only_own_fields(client, db_session, world):
    fu = _farmer_user(db_session, world["farmerA"].id)
    r = client.get("/api/me/fields", headers=_auth(fu))
    assert r.status_code == 200
    ids = {f["id"] for f in r.json()}
    assert world["fieldA"].id in ids
    assert world["fieldB"].id not in ids  # cannot see farmer B's field
    assert all(f["farmer_id"] == world["farmerA"].id for f in r.json())


def test_farmer_without_link_sees_no_fields(client, db_session, world):
    fu = _farmer_user(db_session, None)
    r = client.get("/api/me/fields", headers=_auth(fu))
    assert r.status_code == 200
    assert r.json() == []


def test_farmer_sees_own_assignment(client, db_session, world):
    fu = _farmer_user(db_session, world["farmerA"].id)
    r = client.get(f"/api/me/requests/{world['reqA'].id}/assignment", headers=_auth(fu))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["request_id"] == world["reqA"].id
    assert "assigned_machine" in body  # populated or null with a message
    assert "password_hash" not in str(body)


def test_farmer_cannot_see_another_farmers_assignment(client, db_session, world):
    fu = _farmer_user(db_session, world["farmerA"].id)
    r = client.get(f"/api/me/requests/{world['reqB'].id}/assignment", headers=_auth(fu))
    assert r.status_code == 404


def test_farmer_creates_own_request_spoofed_farmer_id_ignored(client, db_session, world):
    fu = _farmer_user(db_session, world["farmerA"].id)
    payload = {
        "farmer_id": world["farmerB"].id,  # spoof attempt - must be ignored
        "field_id": world["fieldA"].id,
        "operation_type": "Harvesting",
        "requested_date": str(date.today()),
        "urgency": "medium",
    }
    r = client.post("/api/requests", headers=_auth(fu), json=payload)
    assert r.status_code == 201, r.text
    assert r.json()["farmer_id"] == world["farmerA"].id  # forced to their own profile
