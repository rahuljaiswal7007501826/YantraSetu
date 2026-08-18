"""Pydantic schemas for the Analytics API (Phase 9.2).

These mirror the dataclasses produced by app/services/utilization_engine.py.
The engine stays the single source of truth for every calculation; these schemas
only shape its output for the HTTP responses.
"""
from pydantic import BaseModel


class NesComponents(BaseModel):
    """The transparent breakdown behind the Network Efficiency Score."""

    utilization_ratio: float
    demand_coverage_ratio: float
    shortage_relief_ratio: float
    weights: dict
    weighted_contributions: dict


class MachineUtilizationSchema(BaseModel):
    machine_id: int
    chc_id: int
    machine_type: str
    productive_hours: float
    transit_hours: float
    idle_hours: float
    maintenance_hours: float
    active_hours: float
    schedulable_hours: float
    utilization_pct: float


class ChcUtilizationSchema(BaseModel):
    chc_id: int
    chc_name: str
    machine_count: int
    active_hours: float
    idle_hours: float
    schedulable_hours: float
    utilization_pct: float


class AnalyticsSummary(BaseModel):
    """Network-wide KPI roll-up for GET /api/analytics/summary."""

    # Utilization
    network_utilization_pct: float
    total_active_hours: float
    total_productive_hours: float
    total_transit_hours: float
    total_idle_hours: float
    total_maintenance_hours: float
    total_schedulable_hours: float
    machines_counted: int
    # Demand coverage
    demand_coverage_pct: float
    served_requests: int
    non_cancelled_requests: int
    total_requests: int
    # Waiting time (proxy)
    avg_pending_wait_days: float
    pending_requests: int
    wait_metric_label: str
    # Route travel
    avg_route_distance_km: float
    routes_counted: int
    # Relocation impact (approved/completed only)
    relocations_executed: int
    revenue_gained: float
    relocation_cost: float
    net_benefit: float
    # Shortage context
    critical_clusters: int
    clusters_with_demand: int
    # Network Efficiency Score
    network_efficiency_score: float
    nes_components: NesComponents


class UtilizationResponse(BaseModel):
    """Detailed utilization breakdown for GET /api/analytics/utilization."""

    network_utilization_pct: float
    total_active_hours: float
    total_idle_hours: float
    total_maintenance_hours: float
    total_schedulable_hours: float
    machines_counted: int
    per_chc: list[ChcUtilizationSchema]
    per_machine: list[MachineUtilizationSchema]


# --- Before/After impact (Phase 9.3) ---
class StateSnapshotSchema(BaseModel):
    utilization_pct: float
    active_hours: float
    idle_hours: float
    schedulable_hours: float
    demand_coverage_pct: float
    critical_shortages: int


class ShortageDeltaSchema(BaseModel):
    cluster: str
    machine_type: str
    shortage_probability_before: float
    shortage_probability_after: float
    risk_before: str
    risk_after: str


class ImpactResponse(BaseModel):
    """BEFORE vs AFTER the approved/completed relocations."""

    relocations_executed: int
    before: StateSnapshotSchema
    after: StateSnapshotSchema
    utilization_improvement_pct: float
    critical_shortages_before: int
    critical_shortages_after: int
    additional_farmers_served: int
    revenue_gained: float
    relocation_cost: float
    net_benefit: float
    shortage_deltas: list[ShortageDeltaSchema]
