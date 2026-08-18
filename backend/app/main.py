"""
YantraSetu API - application entrypoint.

Wires together configuration, CORS, database table creation on startup, and the
routers: Phase 1 CRUD (CHCs, Machines, Farmers, Fields), the Phase 3 demand
forecast, and the Phase 4 allocation recommender - all mounted under /api.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import (
    allocation,
    analytics,
    chcs,
    dashboard,
    demo,
    farmers,
    fields,
    forecast,
    machines,
    map_data,
    relocations,
    requests,
    routes,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure the database tables exist (dev-stage schema setup).
    init_db()
    yield
    # Shutdown: nothing to clean up yet.


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Intelligent agricultural machinery allocation and rebalancing "
        "platform for Custom Hiring Centres (CHCs)."
    ),
    lifespan=lifespan,
)

# Allow the React dev server (running in the browser) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API routers (everything below lives under the /api prefix) ---
app.include_router(chcs.router, prefix=settings.api_v1_prefix)
app.include_router(machines.router, prefix=settings.api_v1_prefix)
app.include_router(farmers.router, prefix=settings.api_v1_prefix)
app.include_router(fields.router, prefix=settings.api_v1_prefix)
app.include_router(requests.router, prefix=settings.api_v1_prefix)
app.include_router(forecast.router, prefix=settings.api_v1_prefix)
app.include_router(map_data.router, prefix=settings.api_v1_prefix)
app.include_router(allocation.router, prefix=settings.api_v1_prefix)
app.include_router(relocations.router, prefix=settings.api_v1_prefix)
app.include_router(routes.router, prefix=settings.api_v1_prefix)
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(demo.router, prefix=settings.api_v1_prefix)
app.include_router(analytics.router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Meta"])
def root():
    """Friendly landing response pointing to the interactive docs."""
    return {"name": settings.app_name, "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["Meta"])
def health():
    """Liveness probe. Used by us now and by deploy platforms later."""
    return {"status": "healthy", "env": settings.app_env}
