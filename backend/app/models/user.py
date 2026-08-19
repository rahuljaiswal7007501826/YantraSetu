"""User model + role enum (authentication).

A User is a login identity with a role. It is intentionally standalone for this
phase (no FK links to Farmer/CHC yet). Passwords are never stored in plaintext -
only a bcrypt hash lives in `password_hash`.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    """Authorization roles. Stored as the string value in the DB."""

    ADMIN = "ADMIN"                 # maps to the frontend's district_admin
    CHC_MANAGER = "CHC_MANAGER"     # maps to the frontend's chc_operator
    FARMER = "FARMER"               # maps to the frontend's farmer
    OPERATOR = "OPERATOR"           # machine/route operators (new; distinct from manager)


# Roles the public registration endpoint is allowed to create.
PUBLIC_SELF_REGISTER_ROLES = {UserRole.FARMER}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Login identity - unique + indexed. Stored normalized (lowercased/trimmed).
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    # bcrypt hash only - never the plaintext password.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.FARMER.value)
    # Lets an account be disabled without deletion.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Optional link from a FARMER login to their Farmer profile. This is what
    # makes request access owner-scoped at the query level. NULL for staff
    # accounts (admin / chc_manager / operator) and for farmers not yet linked.
    farmer_id: Mapped[int | None] = mapped_column(
        ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
