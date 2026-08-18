"""
SQLAlchemy database layer for YantraSetu.

This module owns the three things the rest of the backend builds on:
  * engine       - the connection pool to PostgreSQL (built from DATABASE_URL)
  * SessionLocal - a factory that hands out short-lived database sessions
  * Base         - the declarative base every ORM model will inherit from

Credentials are never hardcoded here. They come from settings.database_url,
which is loaded from backend/.env.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# The engine owns a pool of real connections to PostgreSQL.
#   pool_pre_ping=True -> test that a pooled connection is still alive before
#                         handing it out, so a stale/dropped connection never
#                         crashes a request (important for long-running servers).
#   pool_recycle=1800  -> proactively replace connections older than 30 minutes.
#   echo=False         -> flip to True temporarily to print the SQL SQLAlchemy runs.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)

# A Session is one "conversation" with the database - typically one API request.
#   autoflush=False        -> we control when pending changes are flushed.
#   expire_on_commit=False -> ORM objects stay usable after commit(), which is
#                             convenient when we return them in an API response.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base. Every model (CHC, Machine, Farmer, Field, ...) inherits it."""

    pass


def get_db():
    """FastAPI dependency: yield a session for one request, always close it.

    Routers will use it like:
        @router.get("/...")
        def handler(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create any tables that don't exist yet (dev-stage schema setup).

    Importing app.models *inside* the function registers every model on
    Base.metadata without risking a circular import at module load time.
    For production we'd move to Alembic migrations; create_all is ideal for dev.
    """
    from app import models  # noqa: F401 - the import is what registers the models

    Base.metadata.create_all(bind=engine)


def verify_connection() -> None:
    """Open a session through SessionLocal and run trivial queries.

    Proves our own engine + session factory (not just raw SQLAlchemy) can reach
    the yantrasetu database. Run it with:  python -m app.database
    """
    with SessionLocal() as db:
        assert db.execute(text("SELECT 1")).scalar() == 1
        version = db.execute(text("SELECT version()")).scalar()
    print("[OK] SQLAlchemy connected via SessionLocal + engine.")
    print(f"     {version}")


if __name__ == "__main__":
    verify_connection()
