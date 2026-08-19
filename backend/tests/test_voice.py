"""Phase 17 - voice transcription proxy tests.

The Bhashini client is mocked (it is never reachable from tests, and requires
real credentials). We verify: success -> {transcript, language}; upstream
failure -> a typed error the frontend can fall back on; missing credentials ->
503 not_configured; oversized clip -> 413; unauthenticated -> 401.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.core.security import create_access_token
from app.database import Base, get_db
import app.models  # noqa: F401
import app.routers.voice as voice_router
from app.main import app
from app.models import User
from app.services.bhashini_client import BhashiniError

WEBM = ("clip.webm", b"\x1a\x45\xdf\xa3-fake-audio-bytes", "audio/webm")


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


@pytest.fixture
def auth(db_session):
    u = User(name="F", email="f@t.com", password_hash="x", role="FARMER", is_active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return {"Authorization": f"Bearer {create_access_token(user_id=u.id, role=u.role, email=u.email)}"}


def test_transcribe_success(client, auth, monkeypatch):
    monkeypatch.setattr(voice_router, "transcribe", lambda *a, **k: "मुझे कटाई चाहिए")
    r = client.post("/api/voice/transcribe", headers=auth, files={"audio": WEBM})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["language"] == "hi"
    assert body["transcript"] == "मुझे कटाई चाहिए"


def test_transcribe_upstream_failure_is_typed(client, auth, monkeypatch):
    def boom(*a, **k):
        raise BhashiniError("compute_http_error", "Bhashini compute returned HTTP 500.")

    monkeypatch.setattr(voice_router, "transcribe", boom)
    r = client.post("/api/voice/transcribe", headers=auth, files={"audio": WEBM})
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "compute_http_error"


def test_transcribe_not_configured_returns_503(client, auth, monkeypatch):
    # Force "no credentials" regardless of any local .env, so the client raises
    # not_configured and the endpoint maps it to a soft 503 for the frontend.
    s = get_settings()
    monkeypatch.setattr(s, "bhashini_user_id", "")
    monkeypatch.setattr(s, "bhashini_api_key", "")
    r = client.post("/api/voice/transcribe", headers=auth, files={"audio": WEBM})
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "not_configured"


def test_transcribe_oversized_clip_413(client, auth, monkeypatch):
    monkeypatch.setattr(get_settings(), "voice_max_upload_bytes", 8)
    big = ("clip.webm", b"x" * 200, "audio/webm")
    r = client.post("/api/voice/transcribe", headers=auth, files={"audio": big})
    assert r.status_code == 413
    assert r.json()["detail"]["code"] == "too_large"


def test_transcribe_requires_authentication(client):
    r = client.post("/api/voice/transcribe", files={"audio": WEBM})
    assert r.status_code == 401
