"""
YantraSetu API - application entrypoint.

Phase 0 only exposes a health check so we can prove the backend runs.
Database wiring, routers, and the intelligence engines arrive in later phases.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Intelligent agricultural machinery allocation and rebalancing "
        "platform for Custom Hiring Centres (CHCs)."
    ),
)

# Allow the React dev server (running in the browser) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Friendly landing response pointing to the interactive docs."""
    return {
        "name": settings.app_name,
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """Liveness probe. Used by us now and by deploy platforms later."""
    return {"status": "healthy", "env": settings.app_env}
