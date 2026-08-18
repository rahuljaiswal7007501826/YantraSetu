"""Alembic environment for YantraSetu.

The database URL is resolved in priority order:
  1. ALEMBIC_DATABASE_URL env var - used for SAFE migration generation/testing
     against a throwaway database, so the real demo DB is never touched.
  2. the application's configured DATABASE_URL (app.config settings / .env).

Credentials are NEVER hardcoded here or in alembic.ini.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make the `app` package importable (this file lives in backend/alembic/).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401 - registers every table on Base.metadata

# Alembic Config object (reads alembic.ini).
config = context.config

# Resolve the DB URL. An explicit ALEMBIC_DATABASE_URL wins so generation/testing
# can run on a throwaway database; only fall back to the app settings (which read
# .env) when it is not set.
_url = os.getenv("ALEMBIC_DATABASE_URL")
if not _url:
    from app.config import get_settings  # noqa: E402

    _url = get_settings().database_url
config.set_main_option("sqlalchemy.url", _url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL without a DB connection (`alembic upgrade head --sql`)."""
    context.configure(
        url=_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
