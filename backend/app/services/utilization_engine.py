"""
Analytics / Utilization Engine  (Phase 9, Step 1).

Turns the raw operational tables into the measurable-impact numbers the
Analytics dashboard will show later. Explainable + deterministic + no ML, in the
same spirit as the other engines, and strictly READ-ONLY (it never writes).

What it computes, and exactly where each number comes from:

  Utilization  (source: MachineAvailability slot hours)
    - Each availability row is a machine's status for a day + time window. We add
      up the hours in each status bucket per machine, then roll up to CHC and to
      the whole network.
    - A machine is "active" when a slot is `booked` (serving a job) or
      `in_transit` (committed to a relocation), "idle" when `available`, and
      "down" when `maintenance`.
    - Utilization % = active hours / schedulable hours, where
      schedulable = active + idle (maintenance is excluded - a machine under
      maintenance is not schedulable, so it neither helps nor hurts the ratio).
    - Machine idle hours = total `available` slot hours.
    - A machine whose maintenance_status is "maintenance" has ALL its slot hours
      treated as maintenance (mirrors how the map/dashboard derive status), so a
      down machine never shows phantom idle capacity.

  Demand coverage  (source: DemandRequest.status)
    - served (allocated/scheduled/completed) / non-cancelled requests.

  Avg pending wait - PROXY  (source: DemandRequest.created_at)
    - average days that still-pending requests have been waiting (today - created_at).
    - This is a PROXY, clearly labelled everywhere: we do not persist a booking /
      service timestamp, so the true "request -> served" wait cannot be measured.

  Route travel  (source: persisted Route rows)
    - average total_distance_km across saved routes.

  Relocation impact  (source: RelocationRecommendation, approved/completed only)
    - number executed, revenue gained, relocation cost, net benefit (summed).

  Network Efficiency Score (NES, 0-100)
      NES = 100 * ( 0.40*utilization_ratio
                  + 0.35*demand_coverage_ratio
                  + 0.25*shortage_relief_ratio )
    - utilization_ratio     = network utilization % / 100
    - demand_coverage_ratio = served / non-cancelled
    - shortage_relief_ratio = 1 - (critical clusters / clusters with demand)
    - The critical/cluster counts come from demand_engine.analyze_demand(), which
      we REUSE - the demand/shortage scoring is not re-implemented here.

All weights and status sets live in one AnalyticsConfig. Nothing about the demo
(Cluster B, machine #98, ...) is hardcoded. Every division is guarded so empty
data returns 0 (or a sensible default) instead of raising.

Try it (from the backend/ folder):
    .venv\\Scripts\\python.exe -m app.services.utilization_engine
"""
from dataclasses import asdict, dataclass, field
from datetime import date, time as time_t

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    CHC,
    DemandRequest,
    Machine,
    MachineAvailability,
    RelocationRecommendation,
    Route,
)
from app.services.demand_engine import analyze_demand


# --------------------------------------------------------------------------
# Configuration - every tunable knob in one place (weights + status sets).
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class AnalyticsConfig:
    # NES weights (must sum to 1.0).
    w_utilization: float = 0.40
    w_coverage: float = 0.35
    w_shortage_relief: float = 0.25

    # Which MachineAvailability statuses count as what, for utilization.
    productive_statuses: tuple[str, ...] = ("booked",)          # actually serving
    transit_statuses: tuple[str, ...] = ("in_transit",)         # committed to a move
    idle_statuses: tuple[str, ...] = ("available",)             # free but unused
    maintenance_statuses: tuple[str, ...] = ("maintenance",)    # not schedulable

    # DemandRequest lifecycle buckets.
    served_request_statuses: tuple[str, ...] = ("allocated", "scheduled", "completed")
    cancelled_request_statuses: tuple[str, ...] = ("cancelled",)

    # A relocation only "counts" as a real action once an operator acted on it.
    executed_relocation_statuses: tuple[str, ...] = ("approved", "completed")


DEFAULT_CONFIG = AnalyticsConfig()


# --------------------------------------------------------------------------
# Structured results (JSON-friendly via to_dict()) - ready for the API later.
# --------------------------------------------------------------------------
@dataclass
class MachineUtilization:
    machine_id: int
    chc_id: int
    machine_type: str
    productive_hours: float   # booked
    transit_hours: float      # in_transit
    idle_hours: float         # available
    maintenance_hours: float  # maintenance (excluded from schedulable)
    active_hours: float       # productive + transit
    schedulable_hours: float  # active + idle
    utilization_pct: float    # 100 * active / schedulable (0 if none)


@dataclass
class ChcUtilization:
    chc_id: int
    chc_name: str
    machine_count: int
    active_hours: float
    idle_hours: float
    schedulable_hours: float
    utilization_pct: float


@dataclass
class AnalyticsSummary:
    # --- Utilization (network roll-up) ---
    network_utilization_pct: float
    total_active_hours: float
    total_productive_hours: float
    total_transit_hours: float
    total_idle_hours: float
    total_maintenance_hours: float
    total_schedulable_hours: float
    machines_counted: int

    # --- Demand coverage ---
    demand_coverage_pct: float
    served_requests: int
    non_cancelled_requests: int
    total_requests: int

    # --- Waiting time (PROXY - see module docstring) ---
    avg_pending_wait_days: float
    pending_requests: int
    wait_metric_label: str

    # --- Route travel ---
    avg_route_distance_km: float
    routes_counted: int

    # --- Relocation impact (approved/completed only) ---
    relocations_executed: int
    revenue_gained: float
    relocation_cost: float
    net_benefit: float

    # --- Shortage context (inputs to NES, from demand_engine) ---
    critical_clusters: int
    clusters_with_demand: int

    # --- Network Efficiency Score ---
    network_efficiency_score: float
    nes_components: dict

    # --- Optional breakdowns ---
    per_chc: list[ChcUtilization] = field(default_factory=list)
    per_machine: list[MachineUtilization] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Small helpers.
# --------------------------------------------------------------------------
def _slot_hours(start: time_t, end: time_t) -> float:
    """Hours between two same-day times. Negative/overnight spans clamp to 0."""
    start_min = start.hour * 60 + start.minute + start.second / 60
    end_min = end.hour * 60 + end.minute + end.second / 60
    return max(0.0, end_min - start_min) / 60.0


def _safe_div(numerator: float, denominator: float) -> float:
    """Divide, returning 0.0 when the denominator is 0 (empty-data safety)."""
    return numerator / denominator if denominator else 0.0


# --------------------------------------------------------------------------
# Individual metric calculators (each pure: read DB -> return values).
# --------------------------------------------------------------------------
def machine_utilizations(
    db: Session, config: AnalyticsConfig = DEFAULT_CONFIG
) -> list[MachineUtilization]:
    """Per-machine utilization from MachineAvailability slot hours.

    Every machine is included (even with no slots -> 0 hours -> 0% utilization),
    so counts and roll-ups are complete.
    """
    # Start every machine at zero so machines without any slots still appear.
    acc: dict[int, dict] = {}
    for mid, chc_id, mtype, m_status in db.execute(
        select(Machine.id, Machine.chc_id, Machine.machine_type, Machine.maintenance_status)
    ).all():
        acc[mid] = {
            "chc_id": chc_id,
            "machine_type": mtype,
            "maintenance_flag": m_status == "maintenance",
            "productive": 0.0,
            "transit": 0.0,
            "idle": 0.0,
            "maintenance": 0.0,
        }

    # Add each availability slot's hours into the right bucket.
    for mid, slot_status, start, end in db.execute(
        select(
            MachineAvailability.machine_id,
            MachineAvailability.status,
            MachineAvailability.start_time,
            MachineAvailability.end_time,
        )
    ).all():
        bucket = acc.get(mid)
        if bucket is None:
            continue  # slot for an unknown machine; ignore defensively
        hours = _slot_hours(start, end)
        # A machine flagged for maintenance is entirely "down" regardless of what
        # its individual slots say (consistent with the map/dashboard derivation).
        status = "maintenance" if bucket["maintenance_flag"] else slot_status
        if status in config.maintenance_statuses:
            bucket["maintenance"] += hours
        elif status in config.productive_statuses:
            bucket["productive"] += hours
        elif status in config.transit_statuses:
            bucket["transit"] += hours
        elif status in config.idle_statuses:
            bucket["idle"] += hours
        # Unknown statuses are ignored so they can't distort the ratio.

    out: list[MachineUtilization] = []
    for mid in sorted(acc):  # sorted -> deterministic ordering
        b = acc[mid]
        active = b["productive"] + b["transit"]
        schedulable = active + b["idle"]
        out.append(MachineUtilization(
            machine_id=mid,
            chc_id=b["chc_id"],
            machine_type=b["machine_type"],
            productive_hours=round(b["productive"], 2),
            transit_hours=round(b["transit"], 2),
            idle_hours=round(b["idle"], 2),
            maintenance_hours=round(b["maintenance"], 2),
            active_hours=round(active, 2),
            schedulable_hours=round(schedulable, 2),
            utilization_pct=round(_safe_div(active, schedulable) * 100, 1),
        ))
    return out


def chc_utilizations(
    db: Session,
    config: AnalyticsConfig = DEFAULT_CONFIG,
    machine_utils: list[MachineUtilization] | None = None,
) -> list[ChcUtilization]:
    """Roll per-machine utilization up to each CHC."""
    machine_utils = machine_utils if machine_utils is not None else machine_utilizations(db, config)
    names = {c.id: c.name for c in db.scalars(select(CHC)).all()}

    agg: dict[int, dict] = {}
    for m in machine_utils:
        g = agg.setdefault(m.chc_id, {"count": 0, "active": 0.0, "idle": 0.0})
        g["count"] += 1
        g["active"] += m.active_hours
        g["idle"] += m.idle_hours

    out: list[ChcUtilization] = []
    for chc_id in sorted(agg):
        g = agg[chc_id]
        schedulable = g["active"] + g["idle"]
        out.append(ChcUtilization(
            chc_id=chc_id,
            chc_name=names.get(chc_id, ""),
            machine_count=g["count"],
            active_hours=round(g["active"], 2),
            idle_hours=round(g["idle"], 2),
            schedulable_hours=round(schedulable, 2),
            utilization_pct=round(_safe_div(g["active"], schedulable) * 100, 1),
        ))
    return out


def demand_coverage(db: Session, config: AnalyticsConfig = DEFAULT_CONFIG) -> dict:
    """Share of (non-cancelled) requests that have been served."""
    counts = dict(
        db.execute(
            select(DemandRequest.status, func.count()).group_by(DemandRequest.status)
        ).all()
    )
    total = sum(counts.values())
    served = sum(counts.get(s, 0) for s in config.served_request_statuses)
    cancelled = sum(counts.get(s, 0) for s in config.cancelled_request_statuses)
    non_cancelled = total - cancelled
    return {
        "served": served,
        "cancelled": cancelled,
        "non_cancelled": non_cancelled,
        "total": total,
        "coverage_pct": round(_safe_div(served, non_cancelled) * 100, 1),
    }


def avg_pending_wait_days(
    db: Session, as_of: date | None = None
) -> dict:
    """PROXY for farmer waiting time.

    Average number of days that still-pending requests have been waiting, using
    created_at (today - created_at). This is NOT the true request->service wait
    (we don't persist a service timestamp); it is explicitly a proxy.
    """
    today = as_of or date.today()
    created_ats = db.scalars(
        select(DemandRequest.created_at).where(DemandRequest.status == "pending")
    ).all()
    waits = [max(0, (today - c.date()).days) for c in created_ats if c is not None]
    return {
        "avg_pending_wait_days": round(_safe_div(sum(waits), len(waits)), 1),
        "pending_requests": len(waits),
    }


def avg_route_distance(db: Session) -> dict:
    """Average total_distance_km across persisted routes."""
    distances = db.scalars(select(Route.total_distance_km)).all()
    return {
        "avg_route_distance_km": round(_safe_div(sum(distances), len(distances)), 2),
        "routes_counted": len(distances),
    }


def relocation_totals(db: Session, config: AnalyticsConfig = DEFAULT_CONFIG) -> dict:
    """Summed impact of relocations that were actually acted on (approved/completed).

    Pending/rejected recommendations are intentionally excluded - they are not
    actions the network has taken.
    """
    rows = db.execute(
        select(
            RelocationRecommendation.expected_revenue,
            RelocationRecommendation.relocation_cost,
            RelocationRecommendation.net_benefit,
        ).where(RelocationRecommendation.status.in_(config.executed_relocation_statuses))
    ).all()
    return {
        "relocations_executed": len(rows),
        "revenue_gained": round(sum(r[0] for r in rows), 0),
        "relocation_cost": round(sum(r[1] for r in rows), 0),
        "net_benefit": round(sum(r[2] for r in rows), 0),
    }


def shortage_context(db: Session, as_of: date | None = None) -> dict:
    """Critical vs total clusters-with-demand, reused from the demand engine.

    We call analyze_demand() (the single source of truth for shortages) and only
    count clusters here - no scoring is re-implemented.
    """
    insights = analyze_demand(db, as_of=as_of) if as_of else analyze_demand(db)
    clusters_with_demand = {i.cluster for i in insights}
    critical_clusters = {i.cluster for i in insights if i.risk_level == "CRITICAL"}
    return {
        "clusters_with_demand": len(clusters_with_demand),
        "critical_clusters": len(critical_clusters),
    }


def network_efficiency_score(
    utilization_ratio: float,
    coverage_ratio: float,
    shortage_relief_ratio: float,
    config: AnalyticsConfig = DEFAULT_CONFIG,
) -> dict:
    """Weighted 0-100 blend of the three real, normalized components."""
    contrib_util = config.w_utilization * utilization_ratio
    contrib_cov = config.w_coverage * coverage_ratio
    contrib_relief = config.w_shortage_relief * shortage_relief_ratio
    score = 100.0 * (contrib_util + contrib_cov + contrib_relief)
    score = max(0.0, min(100.0, score))  # clamp for safety
    return {
        "network_efficiency_score": round(score, 1),
        "components": {
            "utilization_ratio": round(utilization_ratio, 3),
            "demand_coverage_ratio": round(coverage_ratio, 3),
            "shortage_relief_ratio": round(shortage_relief_ratio, 3),
            "weights": {
                "utilization": config.w_utilization,
                "coverage": config.w_coverage,
                "shortage_relief": config.w_shortage_relief,
            },
            "weighted_contributions": {
                "utilization": round(100 * contrib_util, 1),
                "coverage": round(100 * contrib_cov, 1),
                "shortage_relief": round(100 * contrib_relief, 1),
            },
        },
    }


# --------------------------------------------------------------------------
# Main entry point - assemble the full analytics summary.
# --------------------------------------------------------------------------
def compute_analytics(
    db: Session,
    config: AnalyticsConfig = DEFAULT_CONFIG,
    as_of: date | None = None,
    include_detail: bool = True,
) -> AnalyticsSummary:
    """Compute every current-state analytics metric in one deterministic pass."""
    m_utils = machine_utilizations(db, config)
    c_utils = chc_utilizations(db, config, m_utils)

    # Network roll-up from per-machine numbers.
    productive = sum(m.productive_hours for m in m_utils)
    transit = sum(m.transit_hours for m in m_utils)
    idle = sum(m.idle_hours for m in m_utils)
    maintenance = sum(m.maintenance_hours for m in m_utils)
    active = productive + transit
    schedulable = active + idle
    network_util_pct = round(_safe_div(active, schedulable) * 100, 1)

    coverage = demand_coverage(db, config)
    wait = avg_pending_wait_days(db, as_of)
    routes = avg_route_distance(db)
    relocations = relocation_totals(db, config)
    shortage = shortage_context(db, as_of)

    # NES component ratios (all guarded against divide-by-zero).
    utilization_ratio = network_util_pct / 100.0
    coverage_ratio = _safe_div(coverage["served"], coverage["non_cancelled"])
    # Shortage relief = how free of critical shortages the network is.
    #   - demand present : 1 - (critical clusters / clusters with demand)
    #   - machines but no demand right now : fully relieved (1.0)
    #   - EMPTY network (no machines AND no demand) : nothing to score -> 0.0,
    #     so NES comes out 0.0 instead of the degenerate 0.25*1.0 = 25. This only
    #     picks the relief *input* for the empty case; the NES formula is unchanged.
    network_is_empty = len(m_utils) == 0 and shortage["clusters_with_demand"] == 0
    if shortage["clusters_with_demand"]:
        shortage_relief_ratio = 1.0 - _safe_div(
            shortage["critical_clusters"], shortage["clusters_with_demand"]
        )
    elif network_is_empty:
        shortage_relief_ratio = 0.0
    else:
        shortage_relief_ratio = 1.0
    nes = network_efficiency_score(
        utilization_ratio, coverage_ratio, shortage_relief_ratio, config
    )

    return AnalyticsSummary(
        network_utilization_pct=network_util_pct,
        total_active_hours=round(active, 2),
        total_productive_hours=round(productive, 2),
        total_transit_hours=round(transit, 2),
        total_idle_hours=round(idle, 2),
        total_maintenance_hours=round(maintenance, 2),
        total_schedulable_hours=round(schedulable, 2),
        machines_counted=len(m_utils),
        demand_coverage_pct=coverage["coverage_pct"],
        served_requests=coverage["served"],
        non_cancelled_requests=coverage["non_cancelled"],
        total_requests=coverage["total"],
        avg_pending_wait_days=wait["avg_pending_wait_days"],
        pending_requests=wait["pending_requests"],
        wait_metric_label="Avg Pending Wait (proxy)",
        avg_route_distance_km=routes["avg_route_distance_km"],
        routes_counted=routes["routes_counted"],
        relocations_executed=relocations["relocations_executed"],
        revenue_gained=relocations["revenue_gained"],
        relocation_cost=relocations["relocation_cost"],
        net_benefit=relocations["net_benefit"],
        critical_clusters=shortage["critical_clusters"],
        clusters_with_demand=shortage["clusters_with_demand"],
        network_efficiency_score=nes["network_efficiency_score"],
        nes_components=nes["components"],
        per_chc=c_utils if include_detail else [],
        per_machine=m_utils if include_detail else [],
    )


if __name__ == "__main__":
    from app.database import SessionLocal

    with SessionLocal() as session:
        a = compute_analytics(session)
        b = compute_analytics(session)  # second pass -> determinism check

    deterministic = a.to_dict() == b.to_dict()

    print("\n=== YantraSetu Analytics (Phase 9.1 engine) ===")
    print(f"deterministic re-run: {deterministic}")

    print("\n--- Utilization (from MachineAvailability hours) ---")
    print(f"  network utilization : {a.network_utilization_pct}%")
    print(f"  active hours        : {a.total_active_hours}  "
          f"(productive {a.total_productive_hours} + transit {a.total_transit_hours})")
    print(f"  idle hours          : {a.total_idle_hours}")
    print(f"  maintenance hours   : {a.total_maintenance_hours}")
    print(f"  schedulable hours   : {a.total_schedulable_hours}")
    print(f"  machines counted    : {a.machines_counted}")

    print("\n--- Per-CHC utilization ---")
    print(f"  {'CHC':<28}{'MACHINES':>9}{'ACTIVE h':>10}{'IDLE h':>9}{'UTIL %':>8}")
    for c in a.per_chc:
        print(f"  {c.chc_name[:27]:<28}{c.machine_count:>9}{c.active_hours:>10}"
              f"{c.idle_hours:>9}{c.utilization_pct:>8}")

    print("\n--- Demand coverage (from DemandRequest.status) ---")
    print(f"  coverage            : {a.demand_coverage_pct}%  "
          f"(served {a.served_requests} / non-cancelled {a.non_cancelled_requests}; "
          f"total {a.total_requests})")

    print("\n--- Farmer waiting time ---")
    print(f"  {a.wait_metric_label}: {a.avg_pending_wait_days} days  "
          f"over {a.pending_requests} pending requests  [PROXY - uses created_at]")

    print("\n--- Route travel (from persisted Route rows) ---")
    print(f"  avg route distance  : {a.avg_route_distance_km} km  "
          f"over {a.routes_counted} routes")

    print("\n--- Relocation impact (approved/completed only) ---")
    print(f"  relocations executed: {a.relocations_executed}")
    print(f"  revenue gained      : Rs {a.revenue_gained:.0f}")
    print(f"  relocation cost     : Rs {a.relocation_cost:.0f}")
    print(f"  net benefit         : Rs {a.net_benefit:.0f}")

    print("\n--- Network Efficiency Score ---")
    comp = a.nes_components
    print(f"  NES                 : {a.network_efficiency_score} / 100")
    print(f"    utilization_ratio     = {comp['utilization_ratio']}  "
          f"(x{comp['weights']['utilization']} -> {comp['weighted_contributions']['utilization']})")
    print(f"    demand_coverage_ratio = {comp['demand_coverage_ratio']}  "
          f"(x{comp['weights']['coverage']} -> {comp['weighted_contributions']['coverage']})")
    print(f"    shortage_relief_ratio = {comp['shortage_relief_ratio']}  "
          f"(x{comp['weights']['shortage_relief']} -> {comp['weighted_contributions']['shortage_relief']})")
    print(f"    critical clusters {a.critical_clusters} / clusters with demand {a.clusters_with_demand}")
    print()
