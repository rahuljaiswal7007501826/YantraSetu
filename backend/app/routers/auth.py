"""Authentication endpoints. Mounted at /api/auth.

  POST /api/auth/register - public self-registration (FARMER only)
  POST /api/auth/login    - JSON email+password -> JWT access token
  GET  /api/auth/me       - the current authenticated user
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User, UserRole
from app.models.user import PUBLIC_SELF_REGISTER_ROLES
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["Auth"])


def _normalize_email(email: str) -> str:
    return str(email).strip().lower()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new account. Public registration is limited to the FARMER role."""
    # Resolve the requested role. Omitted -> FARMER.
    if payload.role is None:
        role = UserRole.FARMER
    else:
        try:
            role = UserRole(payload.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown role '{payload.role}'.",
            )
        if role not in PUBLIC_SELF_REGISTER_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Public registration is only allowed for the FARMER role. "
                    "Privileged roles are assigned by an administrator."
                ),
            )

    email = _normalize_email(payload.email)
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=role.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Verify credentials and return a signed JWT access token."""
    email = _normalize_email(payload.email)
    user = db.scalar(select(User).where(User.email == email))
    # Generic message on purpose: never reveal whether the email exists.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )
    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user
