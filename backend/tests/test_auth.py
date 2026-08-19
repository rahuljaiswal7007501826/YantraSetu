"""Auth foundation tests (Step G).

Covers password hashing, JWT create/validate, the register/login/me logic, and
the RBAC dependencies. httpx/TestClient is not installed, so we call the router
and dependency functions directly with the in-memory `session` fixture and
assert on the HTTPException each path raises. This exercises the real logic
(status codes, normalization, role gating) without the HTTP layer.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import security as security_mod
from app.core.deps import get_current_user, require_role, require_roles
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import User, UserRole
from app.routers.auth import login, register
from app.schemas.auth import LoginRequest, UserCreate, UserRead


# --------------------------------------------------------------------------- #
# password hashing
# --------------------------------------------------------------------------- #
def test_hash_password_is_not_plaintext():
    h = hash_password("secret123")
    assert h != "secret123"
    assert h.startswith("$2")  # bcrypt hashes start with $2a/$2b


def test_verify_password_true_and_false():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True
    assert verify_password("wrong-password", h) is False


def test_hash_password_uses_random_salt():
    # Same input -> different hashes (unique per-hash salt).
    assert hash_password("secret123") != hash_password("secret123")


def test_verify_password_rejects_garbage_hash():
    assert verify_password("secret123", "not-a-real-hash") is False


def test_hash_password_handles_over_72_bytes():
    long_pw = "a" * 100  # bcrypt only uses the first 72 bytes; must not raise
    h = hash_password(long_pw)
    assert verify_password(long_pw, h) is True


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
def test_jwt_roundtrip_contains_expected_claims():
    token = create_access_token(user_id=42, role=UserRole.FARMER.value, email="a@b.com")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "FARMER"
    assert payload["email"] == "a@b.com"
    assert payload["type"] == "access"
    assert "exp" in payload and "iat" in payload


def test_jwt_expired_token_rejected():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "1", "role": "FARMER", "email": "a@b.com", "type": "access",
            "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1),
        },
        security_mod.settings.secret_key,
        algorithm=security_mod.settings.algorithm,
    )
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token)


def test_jwt_wrong_secret_rejected():
    token = create_access_token(user_id=1, role="FARMER", email="a@b.com")
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, "a-different-secret", algorithms=[security_mod.settings.algorithm])


# --------------------------------------------------------------------------- #
# register
# --------------------------------------------------------------------------- #
def test_register_defaults_to_farmer_and_normalizes_email(session):
    user = register(UserCreate(name="Asha", email="Asha@Example.com", password="password1"), db=session)
    assert user.role == "FARMER"
    assert user.email == "asha@example.com"          # normalized: trimmed + lowercased
    assert user.password_hash != "password1"          # stored hashed, never plaintext


def test_register_rejects_privileged_roles(session):
    for role in ("ADMIN", "CHC_MANAGER", "OPERATOR"):
        with pytest.raises(HTTPException) as exc:
            register(
                UserCreate(name="X", email=f"{role.lower()}@x.com", password="password1", role=role),
                db=session,
            )
        assert exc.value.status_code == 403


def test_register_unknown_role_is_422(session):
    with pytest.raises(HTTPException) as exc:
        register(UserCreate(name="X", email="u@x.com", password="password1", role="SUPERUSER"), db=session)
    assert exc.value.status_code == 422


def test_register_duplicate_email_is_409(session):
    register(UserCreate(name="A", email="dup@x.com", password="password1"), db=session)
    with pytest.raises(HTTPException) as exc:
        # Different case -> still a duplicate after normalization.
        register(UserCreate(name="B", email="DUP@x.com", password="password2"), db=session)
    assert exc.value.status_code == 409


def test_userread_never_exposes_password_hash(session):
    user = register(UserCreate(name="A", email="hide@x.com", password="password1"), db=session)
    dumped = UserRead.model_validate(user).model_dump()
    assert "password_hash" not in dumped
    assert dumped["email"] == "hide@x.com"


# --------------------------------------------------------------------------- #
# login
# --------------------------------------------------------------------------- #
def test_login_success_returns_bearer_token(session):
    register(UserCreate(name="A", email="log@x.com", password="password1"), db=session)
    resp = login(LoginRequest(email="LOG@x.com", password="password1"), db=session)
    assert resp.token_type == "bearer"
    payload = decode_access_token(resp.access_token)
    assert payload["email"] == "log@x.com"
    assert payload["role"] == "FARMER"


def test_login_wrong_password_is_401(session):
    register(UserCreate(name="A", email="wp@x.com", password="password1"), db=session)
    with pytest.raises(HTTPException) as exc:
        login(LoginRequest(email="wp@x.com", password="not-the-password"), db=session)
    assert exc.value.status_code == 401


def test_login_unknown_email_is_401(session):
    with pytest.raises(HTTPException) as exc:
        login(LoginRequest(email="ghost@x.com", password="whatever1"), db=session)
    assert exc.value.status_code == 401


def test_login_disabled_account_is_403(session):
    user = register(UserCreate(name="A", email="dis@x.com", password="password1"), db=session)
    user.is_active = False
    session.commit()
    with pytest.raises(HTTPException) as exc:
        login(LoginRequest(email="dis@x.com", password="password1"), db=session)
    assert exc.value.status_code == 403


# --------------------------------------------------------------------------- #
# get_current_user
# --------------------------------------------------------------------------- #
def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_get_current_user_valid_token(session):
    user = register(UserCreate(name="A", email="me@x.com", password="password1"), db=session)
    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    got = get_current_user(credentials=_creds(token), db=session)
    assert got.id == user.id
    assert got.email == "me@x.com"


def test_get_current_user_missing_credentials_401(session):
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None, db=session)
    assert exc.value.status_code == 401


def test_get_current_user_malformed_token_401(session):
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=_creds("garbage.token.value"), db=session)
    assert exc.value.status_code == 401


def test_get_current_user_wrong_token_type_401(session):
    user = register(UserCreate(name="A", email="rt@x.com", password="password1"), db=session)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user.id), "role": user.role, "email": user.email, "type": "refresh",
            "iat": now, "exp": now + timedelta(hours=1),
        },
        security_mod.settings.secret_key,
        algorithm=security_mod.settings.algorithm,
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=_creds(token), db=session)
    assert exc.value.status_code == 401


def test_get_current_user_inactive_account_403(session):
    user = register(UserCreate(name="A", email="ia@x.com", password="password1"), db=session)
    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    user.is_active = False
    session.commit()
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=_creds(token), db=session)
    assert exc.value.status_code == 403


# --------------------------------------------------------------------------- #
# require_role / require_roles
# --------------------------------------------------------------------------- #
def _user(role: str) -> User:
    return User(id=1, name="U", email="u@x.com", password_hash="x", role=role, is_active=True)


def test_require_role_allows_matching_role():
    checker = require_role(UserRole.ADMIN)
    admin = _user("ADMIN")
    assert checker(current_user=admin) is admin


def test_require_role_blocks_other_role():
    checker = require_role(UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc:
        checker(current_user=_user("FARMER"))
    assert exc.value.status_code == 403


def test_require_roles_allows_any_listed_role():
    checker = require_roles(UserRole.ADMIN, UserRole.CHC_MANAGER)
    mgr = _user("CHC_MANAGER")
    assert checker(current_user=mgr) is mgr


def test_require_roles_blocks_unlisted_role():
    checker = require_roles(UserRole.ADMIN, UserRole.CHC_MANAGER)
    with pytest.raises(HTTPException) as exc:
        checker(current_user=_user("OPERATOR"))
    assert exc.value.status_code == 403
