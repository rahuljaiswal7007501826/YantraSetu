"""Phase 15 - notification system tests.

HTTP-level tests use TestClient over a dedicated in-memory SQLite engine with
StaticPool (so the request-handler thread shares the seeded DB) and a get_db
override; TestClient is used without `with`, so the app lifespan never runs and
the real database is never touched. Service-level tests use the session directly.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database import Base, get_db
import app.models  # noqa: F401 - registers all tables on Base.metadata
from app.main import app
from app.models import Notification, User
from app.models.notification import NotificationType
from app.services.notification_service import create_notification


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
    yield TestClient(app)  # no `with`: lifespan (init_db) never runs
    app.dependency_overrides.clear()


def _user(db, email, role="FARMER"):
    u = User(name=email.split("@")[0], email=email, password_hash="x", role=role, is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _auth(user):
    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    return {"Authorization": f"Bearer {token}"}


def _note(db, user_id, title="n", body="x", type="request_created", read=False):
    n = create_notification(db, user_id=user_id, type=type, title=title, body=body)
    if read:
        n.is_read = True
    return n


# --------------------------------------------------------------------------- #
# service
# --------------------------------------------------------------------------- #
def test_create_notification_persists(db_session):
    u = _user(db_session, "svc@t.com")
    note = create_notification(
        db_session,
        user_id=u.id,
        type=NotificationType.REQUEST_CREATED,
        title="Request created",
        body="Your request #1 was created.",
        link="/request/1",
        related_id=1,
    )
    db_session.commit()  # the service flushes; the caller owns the commit
    got = db_session.get(Notification, note.id)
    assert got is not None
    assert got.user_id == u.id
    assert got.type == "request_created"
    assert got.title == "Request created"
    assert got.link == "/request/1"
    assert got.related_id == 1
    assert got.is_read is False


def test_create_notification_accepts_raw_string_type(db_session):
    u = _user(db_session, "svc2@t.com")
    note = create_notification(
        db_session, user_id=u.id, type="request_assigned", title="Assigned", body="A machine was assigned."
    )
    db_session.commit()
    assert db_session.get(Notification, note.id).type == "request_assigned"


# --------------------------------------------------------------------------- #
# list - owner scoping
# --------------------------------------------------------------------------- #
def test_list_returns_only_callers_own(client, db_session):
    a = _user(db_session, "a@t.com")
    b = _user(db_session, "b@t.com", role="ADMIN")
    na = _note(db_session, a.id, title="A1")
    nb = _note(db_session, b.id, title="B1")
    db_session.commit()

    r = client.get("/api/me/notifications", headers=_auth(a))
    assert r.status_code == 200
    ids = {n["id"] for n in r.json()}
    assert na.id in ids
    assert nb.id not in ids
    # recipient id is never exposed in the response shape
    assert all("user_id" not in n for n in r.json())


@pytest.mark.parametrize("role", ["FARMER", "CHC_MANAGER", "OPERATOR", "ADMIN"])
def test_list_is_role_agnostic(client, db_session, role):
    u = _user(db_session, f"{role.lower()}@t.com", role=role)
    r = client.get("/api/me/notifications", headers=_auth(u))
    assert r.status_code == 200
    assert r.json() == []  # a brand-new user has none


def test_list_unread_only_filter(client, db_session):
    a = _user(db_session, "a@t.com")
    unread = _note(db_session, a.id, title="unread")
    read = _note(db_session, a.id, title="read", read=True)
    db_session.commit()

    r = client.get("/api/me/notifications", headers=_auth(a), params={"unread_only": "true"})
    ids = {n["id"] for n in r.json()}
    assert unread.id in ids
    assert read.id not in ids


def test_list_respects_limit(client, db_session):
    a = _user(db_session, "a@t.com")
    for i in range(3):
        _note(db_session, a.id, title=f"n{i}")
    db_session.commit()

    r = client.get("/api/me/notifications", headers=_auth(a), params={"limit": 2})
    assert r.status_code == 200
    assert len(r.json()) == 2


# --------------------------------------------------------------------------- #
# unread-count
# --------------------------------------------------------------------------- #
def test_unread_count_matches_actual_unread(client, db_session):
    a = _user(db_session, "a@t.com")
    b = _user(db_session, "b@t.com", role="ADMIN")
    _note(db_session, a.id, title="1")
    _note(db_session, a.id, title="2")
    _note(db_session, a.id, title="3", read=True)  # read -> excluded
    _note(db_session, b.id, title="B")             # other user -> excluded
    db_session.commit()

    r = client.get("/api/me/notifications/unread-count", headers=_auth(a))
    assert r.status_code == 200
    assert r.json()["unread"] == 2


# --------------------------------------------------------------------------- #
# mark one read
# --------------------------------------------------------------------------- #
def test_mark_read_then_idempotent(client, db_session):
    a = _user(db_session, "a@t.com")
    n = _note(db_session, a.id, title="1")
    db_session.commit()

    r1 = client.post(f"/api/me/notifications/{n.id}/read", headers=_auth(a))
    assert r1.status_code == 200 and r1.json()["is_read"] is True

    r2 = client.post(f"/api/me/notifications/{n.id}/read", headers=_auth(a))  # idempotent
    assert r2.status_code == 200 and r2.json()["is_read"] is True

    assert client.get("/api/me/notifications/unread-count", headers=_auth(a)).json()["unread"] == 0


def test_mark_read_rejects_other_users_notification(client, db_session):
    a = _user(db_session, "a@t.com")
    b = _user(db_session, "b@t.com", role="ADMIN")
    nb = _note(db_session, b.id, title="B")
    db_session.commit()

    # A must not be able to touch B's notification (owner-scoping -> 404, not 403)
    assert client.post(f"/api/me/notifications/{nb.id}/read", headers=_auth(a)).status_code == 404
    # ...and B's stays unread
    assert client.get("/api/me/notifications/unread-count", headers=_auth(b)).json()["unread"] == 1


def test_mark_read_unknown_id_404(client, db_session):
    a = _user(db_session, "a@t.com")
    assert client.post("/api/me/notifications/999999/read", headers=_auth(a)).status_code == 404


# --------------------------------------------------------------------------- #
# read-all
# --------------------------------------------------------------------------- #
def test_read_all_marks_only_callers_own(client, db_session):
    a = _user(db_session, "a@t.com")
    b = _user(db_session, "b@t.com", role="ADMIN")
    _note(db_session, a.id, title="1")
    _note(db_session, a.id, title="2")
    _note(db_session, b.id, title="B")
    db_session.commit()

    r = client.post("/api/me/notifications/read-all", headers=_auth(a))
    assert r.status_code == 200 and r.json()["unread"] == 0
    assert client.get("/api/me/notifications/unread-count", headers=_auth(a)).json()["unread"] == 0
    # B untouched
    assert client.get("/api/me/notifications/unread-count", headers=_auth(b)).json()["unread"] == 1


# --------------------------------------------------------------------------- #
# auth
# --------------------------------------------------------------------------- #
def test_endpoints_require_authentication(client):
    assert client.get("/api/me/notifications").status_code == 401
    assert client.get("/api/me/notifications/unread-count").status_code == 401
    assert client.post("/api/me/notifications/1/read").status_code == 401
    assert client.post("/api/me/notifications/read-all").status_code == 401
