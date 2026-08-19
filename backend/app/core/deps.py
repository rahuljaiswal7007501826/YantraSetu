"""Authentication/authorization dependencies.

  * get_current_user - resolves the bearer token to a live, active User row.
  * require_role      - dependency factory allowing exactly one role.
  * require_roles     - dependency factory allowing any of several roles.

NOTE: these are provided for the auth foundation. No existing business endpoint
is protected yet - that is a later, separately-approved step.
"""
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User, UserRole

# Reads "Authorization: Bearer <token>" and renders the Authorize box in /docs.
# auto_error=False so we can raise our own consistent 401 when the header is missing.
_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)
_DISABLED_ERROR = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="This account is disabled.",
)
_FORBIDDEN_ERROR = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You do not have permission to perform this action.",
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Decode the bearer token, load the User, and confirm the account is active."""
    if credentials is None or not credentials.credentials:
        raise _CREDENTIALS_ERROR
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _CREDENTIALS_ERROR

    if payload.get("type") != "access":
        raise _CREDENTIALS_ERROR

    sub = payload.get("sub")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise _CREDENTIALS_ERROR

    user = db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_ERROR
    if not user.is_active:
        raise _DISABLED_ERROR
    return user


def _to_value(role) -> str:
    return role.value if isinstance(role, UserRole) else str(role)


def require_role(role) -> Callable[..., User]:
    """Dependency factory: allow only the given single role."""
    allowed = _to_value(role)

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != allowed:
            raise _FORBIDDEN_ERROR
        return current_user

    return _checker


def require_roles(*roles) -> Callable[..., User]:
    """Dependency factory: allow any one of the given roles."""
    allowed = {_to_value(r) for r in roles}

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise _FORBIDDEN_ERROR
        return current_user

    return _checker
