"""Schemas for farmer self-service (owner-scoped, read-only booking view)."""
from pydantic import BaseModel


class MyAssignedMachine(BaseModel):
    """The single machine the network recommends for a farmer's own request."""

    machine_id: int
    machine_type: str
    chc_name: str
    distance_km: float
    compatible: bool


class MyAssignmentRead(BaseModel):
    """A farmer-facing view of their request's machine assignment.

    `assigned_machine` is populated only when the allocation engine finds a
    suitable machine; otherwise `message` explains why.
    """

    request_id: int
    status: str
    assigned_machine: MyAssignedMachine | None = None
    message: str | None = None
