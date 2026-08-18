# ---------------------------------------------------------------------------
# YantraSetu backend - production image.
# Build context is the backend/ folder:
#   docker build -t yantrasetu-api ./backend
# Secrets (.env) are never copied in - see .dockerignore.
# ---------------------------------------------------------------------------
FROM python:3.13-slim

# No .pyc files, unbuffered logs, no pip cache bloat in the image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libgomp1 is the OpenMP runtime that OR-Tools / NumPy wheels load at import
# time; the slim base image does not include it by default.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first so this layer caches unless requirements change.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source (app/, alembic/, alembic.ini, start.sh, ...).
COPY . ./

# Normalise line endings (in case start.sh was authored on Windows) and make it
# executable, so the shebang works on Linux.
RUN sed -i 's/\r$//' ./start.sh && chmod +x ./start.sh

# Platforms (Render/Railway/Fly) inject $PORT; default to 8000 for local runs.
ENV PORT=8000
EXPOSE 8000

# Production entrypoint: run migrations, then serve (see start.sh).
CMD ["./start.sh"]
