"""Analytics API (Phase 9.2).

Thin read-only layer over app/services/utilization_engine.py. All calculation
lives in the engine; these handlers just call it and shape the response.
Mounted at /api/analytics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analytics import AnalyticsSummary, ImpactResponse, UtilizationResponse
from app.services.impact_engine import compute_impact
from app.services.utilization_engine import compute_analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(db: Session = Depends(get_db)):
    """Network-wide KPI roll-up (utilization, coverage, wait proxy, relocations, NES)."""
    # include_detail=False -> skip the heavy per-machine list; the response model
    # keeps only the summary fields anyway.
    return compute_analytics(db, include_detail=False).to_dict()


@router.get("/utilization", response_model=UtilizationResponse)
def analytics_utilization(db: Session = Depends(get_db)):
    """Per-CHC and per-machine utilization breakdown, plus the network totals."""
    return compute_analytics(db).to_dict()


@router.get("/impact", response_model=ImpactResponse)
def analytics_impact(db: Session = Depends(get_db)):
    """BEFORE vs AFTER the approved relocations (utilization, shortages, financials)."""
    return compute_impact(db).to_dict()
