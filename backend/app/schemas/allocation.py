"""Pydantic schemas for the allocation-recommendation API (Phase 4, Step 2).

These describe the request body and the JSON shape returned by
POST /api/allocation/recommend. The scoring itself lives in
app/services/allocation_engine.py - here we only validate input and rename a few
engine fields to the API's public names.
"""
from pydantic import BaseModel, Field


class AllocationRequestIn(BaseModel):
    """Body for POST /api/allocation/recommend."""

    request_id: int = Field(..., gt=0, examples=[151],
                            description="Id of the DemandRequest to allocate")
    top_n: int = Field(5, ge=1, le=20, description="How many ranked candidates to return")


class AllocationFactors(BaseModel):
    """The explainable 0-1 factor breakdown behind an allocation score."""

    distance_score: float
    urgency_score: float
    compatibility_score: float
    capacity_fit: float
    relocation_cost_score: float
    cluster_efficiency_gain: float
    future_demand_avoidance: float
    weights: dict[str, float]


class MachineRecommendation(BaseModel):
    """One ranked machine candidate."""

    machine_id: int
    machine_type: str
    chc_id: int
    chc_name: str
    score: float = Field(..., description="0-100")
    distance_km: float
    compatible: bool
    relocation_required: bool
    estimated_relocation_cost: float = Field(..., description="Rupees")
    expected_farmers_served: int
    factor_breakdown: AllocationFactors
    explanation: str

    @classmethod
    def from_candidate(cls, c) -> "MachineRecommendation":
        """Map a MachineCandidate (engine dataclass) onto the API schema."""
        return cls(
            machine_id=c.machine_id,
            machine_type=c.machine_type,
            chc_id=c.chc_id,
            chc_name=c.chc_name,
            score=c.score,
            distance_km=c.distance_km,
            compatible=c.compatible,
            relocation_required=c.relocation_required,
            estimated_relocation_cost=c.relocation_cost,
            expected_farmers_served=c.expected_farmers_served,
            factor_breakdown=c.factors,
            explanation=c.reason,
        )


class AllocationResponse(BaseModel):
    """The full response: request context + ranked recommendations."""

    request_id: int
    operation_type: str
    urgency: str
    field_id: int
    farmer_id: int
    farmer_name: str
    candidate_count: int
    recommendations: list[MachineRecommendation]
    # Populated only when there are no candidates, to explain why.
    message: str | None = None
