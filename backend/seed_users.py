"""Seed four demo login users (one per role) for the SIH demonstration.

SYNTHETIC DEMO CREDENTIALS - not for production. All four accounts share the
same password below so they are easy to use while presenting.

    admin@yantrasetu.demo      / demo1234   -> ADMIN         (district admin)
    manager@yantrasetu.demo    / demo1234   -> CHC_MANAGER   (CHC operator)
    operator@yantrasetu.demo   / demo1234   -> OPERATOR      (machine/route operator)
    farmer@yantrasetu.demo     / demo1234   -> FARMER

This script is IDEMPOTENT: re-running it upserts the same emails in place rather
than creating duplicates, so the demo credentials always work.

Run it MANUALLY, only when you want demo login accounts in whatever database
DATABASE_URL currently points to:

    python seed_users.py

It is deliberately NOT wired into seed_database.py, so re-seeding the demo
business data never touches the users table (and vice versa).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import DemandRequest, Farmer, User, UserRole

# Shared demo password. Meets the 8-char minimum enforced by the register schema.
DEMO_PASSWORD = "demo1234"

DEMO_USERS = [
    {"name": "District Admin (Demo)", "email": "admin@yantrasetu.demo", "role": UserRole.ADMIN},
    {"name": "CHC Manager (Demo)", "email": "manager@yantrasetu.demo", "role": UserRole.CHC_MANAGER},
    {"name": "Machine Operator (Demo)", "email": "operator@yantrasetu.demo", "role": UserRole.OPERATOR},
    {"name": "Farmer (Demo)", "email": "farmer@yantrasetu.demo", "role": UserRole.FARMER},
]


def _demo_farmer_id(db: Session) -> int | None:
    """Pick a Farmer to link the demo FARMER login to.

    Prefer the farmer who owns the earliest demand request (so the demo farmer
    actually has requests to view); fall back to the earliest farmer; else None.
    """
    fid = db.scalar(select(DemandRequest.farmer_id).order_by(DemandRequest.id).limit(1))
    if fid is None:
        fid = db.scalar(select(Farmer.id).order_by(Farmer.id).limit(1))
    return fid


def seed_users(db: Session, password: str = DEMO_PASSWORD) -> dict:
    """Idempotently upsert the demo users into the given session.

    The FARMER account is linked to a real Farmer profile so owner-scoped request
    access has data to show. Returns {"created": int, "updated": int, "farmer_id": ...}.
    """
    demo_farmer_id = _demo_farmer_id(db)
    created = updated = 0
    for spec in DEMO_USERS:
        email = spec["email"].strip().lower()
        # Only the FARMER login is tied to a Farmer profile; staff accounts are not.
        linked = demo_farmer_id if spec["role"] == UserRole.FARMER else None
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            db.add(
                User(
                    name=spec["name"],
                    email=email,
                    password_hash=hash_password(password),
                    role=spec["role"].value,
                    is_active=True,
                    farmer_id=linked,
                )
            )
            created += 1
        else:
            # Keep the demo account deterministic on re-run.
            user.name = spec["name"]
            user.role = spec["role"].value
            user.password_hash = hash_password(password)
            user.is_active = True
            user.farmer_id = linked
            updated += 1
    db.commit()
    return {"created": created, "updated": updated, "farmer_id": demo_farmer_id}


def main() -> None:
    from app.config import get_settings

    settings = get_settings()
    # Print only the host/db portion, never the password embedded in the URL.
    safe_target = settings.database_url.split("@")[-1]
    print(f"[seed_users] Target database: {safe_target}")
    print(f"[seed_users] SYNTHETIC DEMO USERS - shared password: {DEMO_PASSWORD}")
    with SessionLocal() as db:
        result = seed_users(db)
    print(
        f"[seed_users] Done. created={result['created']} updated={result['updated']} "
        f"(demo FARMER linked to farmer_id={result['farmer_id']})"
    )
    for spec in DEMO_USERS:
        print(f"    {spec['email']:26} {DEMO_PASSWORD:10} -> {spec['role'].value}")


if __name__ == "__main__":
    main()
