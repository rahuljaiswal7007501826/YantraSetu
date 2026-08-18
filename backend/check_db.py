"""
One-off PostgreSQL connectivity check for YantraSetu (Phase 1, Step 1).

Run it from the backend/ folder AFTER you set DATABASE_URL in .env:

    .venv\\Scripts\\python.exe check_db.py

What it does:
  1. Reads DATABASE_URL from your .env (via app.config) - never prints your password.
  2. Connects to the PostgreSQL server.
  3. Creates the target database (e.g. "yantrasetu") if it does not exist yet.
  4. Connects to that database and prints the server version.

This is a throwaway helper. The real app engine/session comes later in database.py.
"""
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.config import get_settings


def _hint(err: Exception) -> None:
    """Turn a raw driver error into a plain-language next step."""
    msg = str(err).lower()
    if "password authentication failed" in msg:
        print("    -> Wrong username or password. Fix DATABASE_URL in backend/.env")
    elif any(s in msg for s in ("could not connect", "connection refused",
                                "could not translate host", "timeout expired")):
        print("    -> Is PostgreSQL actually running on localhost:5432?")
    elif "does not exist" in msg:
        print("    -> The role or maintenance database does not exist. Check your username.")
    else:
        print(f"    -> {err}")


def main() -> int:
    settings = get_settings()

    try:
        url = make_url(settings.database_url)
    except Exception as e:  # noqa: BLE001 - we want a friendly message
        print(f"[X] DATABASE_URL is not a valid URL: {e}")
        return 1

    if not url.drivername.startswith("postgresql"):
        print(f"[!] DATABASE_URL driver is '{url.drivername}', but PostgreSQL is expected.")
        print("    Set DATABASE_URL=postgresql+psycopg2://... in backend/.env")
        return 1

    if url.username in (None, "YOUR_PG_USER") or (url.password or "") in ("", "YOUR_PG_PASSWORD"):
        print("[!] DATABASE_URL still contains placeholder credentials.")
        print("    Open backend/.env and set your real PostgreSQL username and password.")
        return 1

    target_db = url.database
    print(f"[i] Server:   {url.host}:{url.port}")
    print(f"[i] User:     {url.username}")
    print(f"[i] Database: {target_db}")

    # 1) Ensure the target database exists. We connect to the built-in "postgres"
    #    maintenance database and issue CREATE DATABASE if needed. CREATE DATABASE
    #    cannot run inside a transaction, so we use AUTOCOMMIT.
    admin_url = url.set(database="postgres")
    try:
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": target_db},
            ).scalar()
            if exists:
                print(f"[i] Database '{target_db}' already exists.")
            else:
                conn.execute(text(f'CREATE DATABASE "{target_db}"'))
                print(f"[+] Created database '{target_db}'.")
    except OperationalError as e:
        print("[X] Could not connect to the PostgreSQL server.")
        _hint(e)
        return 1
    except SQLAlchemyError as e:
        print("[X] Could not ensure the database exists.")
        _hint(e)
        return 1

    # 2) Connect to the target database and read the version string.
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
        print("[OK] Connected to the YantraSetu database successfully.")
        print(f"     {version}")
        return 0
    except SQLAlchemyError as e:
        print("[X] Could not connect to the target database.")
        _hint(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
