"""Phase 18 - TTS proxy tests (/api/voice/speak). Bhashini is mocked.

Verifies: success -> base64 audio + {mime, language}; an identical repeated
string is served from cache (no second upstream call) within the TTL; upstream
failure -> a typed error the frontend can fall back on; missing credentials ->
503; empty text -> 400; unauthenticated -> 401.
"""
import base64

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


@pytest.fixture(autouse=True)
def _clear_tts_cache():
    voice_router.clear_tts_cache()
    yield
    voice_router.clear_tts_cache()


def test_speak_success(client, auth, monkeypatch):
    monkeypatch.setattr(voice_router, "synthesize", lambda *a, **k: (b"WAVDATA", "audio/wav"))
    r = client.post("/api/voice/speak", headers=auth, json={"text": "आपका अनुरोध दर्ज हो गया है।"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["language"] == "hi"
    assert body["mime"] == "audio/wav"
    assert body["cached"] is False
    assert base64.b64decode(body["audio_base64"]) == b"WAVDATA"


def test_speak_caches_identical_string(client, auth, monkeypatch):
    calls = {"n": 0}

    def counting(*a, **k):
        calls["n"] += 1
        return b"WAVDATA", "audio/wav"

    monkeypatch.setattr(voice_router, "synthesize", counting)
    payload = {"text": "आपका अनुरोध सफलतापूर्वक दर्ज हो गया है।"}
    r1 = client.post("/api/voice/speak", headers=auth, json=payload)
    r2 = client.post("/api/voice/speak", headers=auth, json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert calls["n"] == 1  # second call served from cache, no upstream hit
    assert r1.json()["cached"] is False
    assert r2.json()["cached"] is True


def test_speak_upstream_failure_is_typed(client, auth, monkeypatch):
    def boom(*a, **k):
        raise BhashiniError("compute_http_error", "Bhashini compute returned HTTP 500.")

    monkeypatch.setattr(voice_router, "synthesize", boom)
    r = client.post("/api/voice/speak", headers=auth, json={"text": "नमस्ते"})
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "compute_http_error"


def test_speak_not_configured_returns_503(client, auth, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "bhashini_user_id", "")
    monkeypatch.setattr(s, "bhashini_api_key", "")
    r = client.post("/api/voice/speak", headers=auth, json={"text": "नमस्ते"})
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "not_configured"


def test_speak_empty_text_400(client, auth):
    r = client.post("/api/voice/speak", headers=auth, json={"text": "   "})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "empty_text"


def test_speak_requires_authentication(client):
    r = client.post("/api/voice/speak", json={"text": "नमस्ते"})
    assert r.status_code == 401
