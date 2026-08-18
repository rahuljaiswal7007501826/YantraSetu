"""Pydantic schemas for the relocation API (Phase 5, Step 2)."""
from datetime import datetime

from pydantic import BaseModel


class RelocationRead(BaseModel):
    """One relocation recommendation, with its financial justification."""

    id: int
    machine_id: int
    machine_type: str
    from_chc_id: int
    from_chc_name: str
    to_cluster: str
    net_benefit: float
    relocation_cost: float
    expected_revenue: float
    expected_farmers_served: int
    status: str
    benefit_breakdown: dict
    explanation: str
    created_at: datetime

    @classmethod
    def from_rec(cls, rec) -> "RelocationRead":
        """Build the API shape from a RelocationRecommendation ORM row.

        Adds two derived fields the model doesn't store directly: the source CHC
        name and a plain-English explanation.
        """
        explanation = (
            f"Move {rec.machine_type} #{rec.machine_id} from "
            f"{rec.from_chc.name if rec.from_chc else 'CHC'} to {rec.to_cluster}: "
            f"serves ~{rec.expected_farmers_served} farmers, "
            f"net benefit Rs {rec.net_benefit:.0f} (status: {rec.status})."
        )
        return cls(
            id=rec.id,
            machine_id=rec.machine_id,
            machine_type=rec.machine_type,
            from_chc_id=rec.from_chc_id,
            from_chc_name=rec.from_chc.name if rec.from_chc else "",
            to_cluster=rec.to_cluster,
            net_benefit=rec.net_benefit,
            relocation_cost=rec.relocation_cost,
            expected_revenue=rec.expected_revenue,
            expected_farmers_served=rec.expected_farmers_served,
            status=rec.status,
            benefit_breakdown=rec.benefit_breakdown or {},
            explanation=explanation,
            created_at=rec.created_at,
        )


class GenerateResponse(BaseModel):
    """Result of asking the engine to (re)generate recommendations."""

    created_count: int
    recommendations: list[RelocationRead]
    message: str
