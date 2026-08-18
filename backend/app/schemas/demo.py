"""Schema for the demo scenario control endpoint (Phase 7.7)."""
from pydantic import BaseModel


class DemoResetResult(BaseModel):
    """Summary of what the demo reset touched, so the UI can confirm it ran."""

    recommendations_reset: int
    machines_restored: int
    availability_rows_restored: int
    message: str
