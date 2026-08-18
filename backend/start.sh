#!/usr/bin/env sh
# Production startup for the YantraSetu backend.
#   1) apply database migrations (Alembic owns the schema in production)
#   2) start the ASGI server
# `set -e` makes the container fail fast if migrations fail, so we never serve
# on a broken or un-migrated schema.
set -e

echo "[start] Applying database migrations (alembic upgrade head)..."
alembic upgrade head

echo "[start] Starting Uvicorn on port ${PORT:-8000} (workers=${WEB_CONCURRENCY:-1})..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}"
