"""Pydantic response schemas for the demand-forecast API (Phase 3, Step 2).

These describe the *shape* of what the forecast endpoints return. They mirror the
DemandInsight dataclass produced by app/services/demand_engine.py, so the router
can stay thin - it just converts engine output into these and returns it.
"""
from pydantic import BaseModel, Field


class DemandFactors(BaseModel):
    """The explainable breakdown behind a demand score (all normalized 0-1)."""

    historical_score: float
    crop_calendar_score: float
    live_request_score: float
    momentum_score: float
    pending_requests: int
    historical_requests: int
    weights: dict[str, float]


class DemandInsightRead(BaseModel):
    """One (cluster, machine_type) demand verdict."""

    cluster: str
    machine_type: str
    demand_score: float = Field(..., description="0-100")
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    expected_requests: int
    available_supply: int = Field(..., description="Idle, operational machines of this type in the cluster")
    shortage_probability: float = Field(..., description="0-1")
    reason: str
    factors: DemandFactors
