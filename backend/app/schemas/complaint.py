"""Pydantic schemas for the complaints API (Phase 19)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Mirror the model enums as Literals for request validation + clear OpenAPI docs.
ComplaintCategoryLiteral = Literal[
    "machine_no_show",
    "machine_breakdown",
    "wrong_machine_type",
    "operator_conduct",
    "chc_service",
    "other",
]
ComplaintStatusLiteral = Literal["open", "in_progress", "resolved", "closed"]


class ComplaintCreate(BaseModel):
    """Body for POST /api/complaints (the farmer's File Complaint form)."""

    category: ComplaintCategoryLiteral
    description: str = Field(..., min_length=1, max_length=2000)
    # Optional context; any/all may be omitted (a general-service complaint).
    demand_request_id: int | None = Field(None, gt=0)
    machine_id: int | None = Field(None, gt=0)
    chc_id: int | None = Field(None, gt=0)


class ComplaintRespondIn(BaseModel):
    """Body for POST /api/complaints/{id}/respond. A response is required."""

    response: str = Field(..., min_length=1, max_length=2000)


class ComplaintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farmer_id: int
    category: str
    description: str
    demand_request_id: int | None = None
    machine_id: int | None = None
    chc_id: int | None = None
    status: str
    staff_response: str | None = None
    responded_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime
