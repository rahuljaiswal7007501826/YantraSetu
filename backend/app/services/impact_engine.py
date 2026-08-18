"""
Before/After Impact Engine  (Phase 9, Step 3).

Answers "what measurable difference did the approved relocations make?" by
computing the network TWICE from the same real data:

  BEFORE - the world with the approved/completed relocations reverted:
           each relocated machine is idle at its home CHC (not moving), so its
           in-transit hours count as idle and its destination cluster gets no
           extra supply.
  AFTER  - the world with those relocations applied:
           each relocated machine is credited to its destination cluster (its
           serviceable capacity relieves that shortage) and counts as active.

Nothing is re-implemented here:
  - shortages come from demand_engine.analyze_demand() via its supply-adjustment
    hook (source cluster for BEFORE, destination cluster for AFTER);
  - utilization comes from utilization_engine (we only shift the relocated
    machines' in-transit hours back to idle for the BEFORE view);
  - the financial totals come straight off the RelocationRecommendation rows.

With ZERO approved relocations, BEFORE and AFTER are identical.

Assumptions / limits:
  - AFTER is a projection: an approved machine is credited to its destination as
    if it will serve there (it may still be physically in transit).
  - Shortage relief uses the demand engine's own supply model (one machine adds
    REQUESTS_PER_MACHINE serviceable jobs to the destination). The farmers/revenue
    figures use each recommendation's own expected values - a separate lens.
  - Demand coverage is unchanged by a relocation (approval does not create a
    booking or mark requests served), so it is reported equal in both states.

Try it (from the backend/ folder):
    .venv\\Scripts\\python.exe -m app.services.impact_engine
"""
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RelocationRecommendation
from app.services.demand_engine import analyze_demand, build_clusters
from app.services.utilization_engine import (
    DEFAULT_CONFIG,
    AnalyticsConfig,
    demand_coverage,
    machine_utilizations,
)


@dataclass
class StateSnapshot:
    """The network's key numbers in one scenario (BEFORE or AFTER)."""

    utilization_pct: float
    active_hours: float
    idle_hours: float
    schedulable_hours: float
    demand_coverage_pct: float
    critical_shortages: int


@dataclass
class ShortageDelta:
    """How a destination shortage changed once the machine was credited to it."""

    cluster: str
    machine_type: str
    shortage_probability_before: float
    shortage_probability_after: float
    risk_before: str
    risk_after: str


@dataclass
class ImpactResult:
    relocations_executed: int
    before: StateSnapshot
    after: StateSnapshot
    utilization_improvement_pct: float
    critical_shortages_before: int
    critical_shortages_after: int
    additional_farmers_served: int
    revenue_gained: float
    relocation_cost: float
    net_benefit: float
    shortage_deltas: list[ShortageDelta] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _critical_count(insights) -> int:
    """Number of CRITICAL (cluster, machine_type) shortages."""
    return sum(1 for i in insights if i.risk_level == "CRITICAL")


def compute_impact(
    db: Session,
    config: AnalyticsConfig = DEFAULT_CONFIG,
    as_of: date | None = None,
) -> ImpactResult:
    """Compute the BEFORE vs AFTER picture for the approved/completed relocations."""
    # --- The action set: relocations an operator actually acted on ---
    action_set = db.scalars(
        select(RelocationRecommendation).where(
            RelocationRecommendation.status.in_(config.executed_relocation_statuses)
        )
    ).all()

    # --- Supply adjustments: BEFORE credits the machine to its source cluster,
    #     AFTER credits it to its destination cluster (relieving that shortage). ---
    _, chc_to_cluster = build_clusters(db)
    before_adj: dict[tuple[str, str], int] = defaultdict(int)
    after_adj: dict[tuple[str, str], int] = defaultdict(int)
    for r in action_set:
        source_cluster = chc_to_cluster.get(r.from_chc_id)
        if source_cluster:
            before_adj[(source_cluster, r.machine_type)] += 1
        after_adj[(r.to_cluster, r.machine_type)] += 1

    before_insights = analyze_demand(
        db, as_of=as_of, supply_adjustments=dict(before_adj) or None
    )
    after_insights = analyze_demand(
        db, as_of=as_of, supply_adjustments=dict(after_adj) or None
    )

    # --- Utilization: current DB is the AFTER state; for BEFORE we move the
    #     relocated machines' in-transit hours back to idle. ---
    m_utils = machine_utilizations(db, config)
    after_active = sum(m.active_hours for m in m_utils)
    after_idle = sum(m.idle_hours for m in m_utils)
    schedulable = after_active + after_idle
    action_ids = {r.machine_id for r in action_set}
    reverted_transit = sum(m.transit_hours for m in m_utils if m.machine_id in action_ids)
    before_active = after_active - reverted_transit
    before_idle = after_idle + reverted_transit

    def _util(active: float) -> float:
        return round(100 * active / schedulable, 1) if schedulable else 0.0

    # Demand coverage is not moved by a relocation (no booking is created).
    coverage_pct = demand_coverage(db, config)["coverage_pct"]

    crit_before = _critical_count(before_insights)
    crit_after = _critical_count(after_insights)

    before = StateSnapshot(
        utilization_pct=_util(before_active),
        active_hours=round(before_active, 2),
        idle_hours=round(before_idle, 2),
        schedulable_hours=round(schedulable, 2),
        demand_coverage_pct=coverage_pct,
        critical_shortages=crit_before,
    )
    after = StateSnapshot(
        utilization_pct=_util(after_active),
        active_hours=round(after_active, 2),
        idle_hours=round(after_idle, 2),
        schedulable_hours=round(schedulable, 2),
        demand_coverage_pct=coverage_pct,
        critical_shortages=crit_after,
    )

    # --- Shortage relief at each destination the action set targeted ---
    before_map = {(i.cluster, i.machine_type): i for i in before_insights}
    after_map = {(i.cluster, i.machine_type): i for i in after_insights}
    deltas: list[ShortageDelta] = []
    for key in sorted({(r.to_cluster, r.machine_type) for r in action_set}):
        b = before_map.get(key)
        a = after_map.get(key)
        if b is None and a is None:
            continue
        deltas.append(ShortageDelta(
            cluster=key[0],
            machine_type=key[1],
            shortage_probability_before=b.shortage_probability if b else 0.0,
            shortage_probability_after=a.shortage_probability if a else 0.0,
            risk_before=b.risk_level if b else "LOW",
            risk_after=a.risk_level if a else "LOW",
        ))

    return ImpactResult(
        relocations_executed=len(action_set),
        before=before,
        after=after,
        utilization_improvement_pct=round(_util(after_active) - _util(before_active), 1),
        critical_shortages_before=crit_before,
        critical_shortages_after=crit_after,
        additional_farmers_served=sum(r.expected_farmers_served for r in action_set),
        revenue_gained=round(sum(r.expected_revenue for r in action_set), 0),
        relocation_cost=round(sum(r.relocation_cost for r in action_set), 0),
        net_benefit=round(sum(r.net_benefit for r in action_set), 0),
        shortage_deltas=deltas,
    )


if __name__ == "__main__":
    from app.database import SessionLocal

    with SessionLocal() as session:
        r = compute_impact(session)

    print("\n=== YantraSetu BEFORE -> AFTER impact (Phase 9.3) ===")
    print(f"relocations executed: {r.relocations_executed}")
    print(f"\n{'':<22}{'BEFORE':>12}{'AFTER':>12}")
    print(f"{'utilization %':<22}{r.before.utilization_pct:>12}{r.after.utilization_pct:>12}")
    print(f"{'idle hours':<22}{r.before.idle_hours:>12}{r.after.idle_hours:>12}")
    print(f"{'demand coverage %':<22}{r.before.demand_coverage_pct:>12}{r.after.demand_coverage_pct:>12}")
    print(f"{'critical shortages':<22}{r.before.critical_shortages:>12}{r.after.critical_shortages:>12}")
    print(f"\nutilization improvement: {r.utilization_improvement_pct} pts")
    print(f"additional farmers served: {r.additional_farmers_served}")
    print(f"revenue gained : Rs {r.revenue_gained:.0f}")
    print(f"relocation cost: Rs {r.relocation_cost:.0f}")
    print(f"net benefit    : Rs {r.net_benefit:.0f}")
    if r.shortage_deltas:
        print("\nshortage relief at destinations:")
        for d in r.shortage_deltas:
            print(f"  {d.cluster} / {d.machine_type}: "
                  f"{d.shortage_probability_before*100:.0f}% ({d.risk_before}) -> "
                  f"{d.shortage_probability_after*100:.0f}% ({d.risk_after})")
    print()
