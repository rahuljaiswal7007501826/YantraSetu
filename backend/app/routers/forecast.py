"""Forecast API - exposes the Demand Intelligence Engine over HTTP.

This layer is deliberately THIN. All scoring lives in
app/services/demand_engine.py; here we only call it and shape the result into
response schemas. Mounted at /api/forecast.
"""
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.forecast import DemandInsightRead
from app.services.demand_engine import analyze_demand, get_shortages

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get("", response_model=list[DemandInsightRead])
def read_forecast(db: Session = Depends(get_db)):
    """Full demand picture for every (cluster, machine type) that has demand,
    sorted by shortage risk (highest first)."""
    insights = analyze_demand(db)
    return [DemandInsightRead.model_validate(i.to_dict()) for i in insights]


@router.get("/shortages", response_model=list[DemandInsightRead])
def read_shortages(
    min_risk: Literal["HIGH", "CRITICAL"] = "HIGH",
    db: Session = Depends(get_db),
):
    """Only the shortage / high-risk pairs.

    Defaults to HIGH-and-above; pass ?min_risk=CRITICAL to narrow to the most
    severe shortages only.
    """
    insights = analyze_demand(db)
    shortages = get_shortages(insights, min_risk=min_risk)
    return [DemandInsightRead.model_validate(i.to_dict()) for i in shortages]
