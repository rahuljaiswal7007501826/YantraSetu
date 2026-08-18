"""Pydantic schema for the Overview dashboard roll-up (Phase 7.6)."""
from pydantic import BaseModel


class AdminDashboard(BaseModel):
    """Network-wide KPIs for the Overview screen.

    Pure aggregation: counts from the database plus shortage figures reused from
    the demand engine. No new business logic lives here.
    """

    total_chcs: int
    total_machines: int
    total_farmers: int
    pending_requests: int
    # Machine status today (mirrors the map's derivation).
    machines_available: int
    machines_booked: int
    machines_in_transit: int
    machines_maintenance: int
    # Demand engine roll-up.
    critical_shortages: int
    high_risk_areas: int
    # Relocation engine roll-up (pending, awaiting operator approval).
    pending_relocations: int
    potential_net_benefit: float
