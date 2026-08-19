"""Pydantic schemas for authentication (register / login / token / me).

UserRead deliberately omits `password_hash` so a hash can never leak through the API.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Registration payload.

    `role` is optional. Public registration only honors FARMER; the router
    rejects any attempt to self-register a privileged role.
    """

    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    # min 8 keeps demo passwords sane; bcrypt itself only uses the first 72 bytes.
    password: str = Field(..., min_length=8, max_length=128)
    role: str | None = Field(
        default=None,
        description="Optional. Public registration only allows FARMER.",
    )


class UserRead(BaseModel):
    """Public user shape returned by the API - never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    farmer_id: int | None = None
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
