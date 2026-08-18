"""
Cross-CHC Relocation Engine  (Phase 5, Step 1).

Answers: "which idle machine, from which CHC, should be moved to a shortage
cluster - and is the move actually worth it?"

    NetBenefit(move machine -> cluster B) =
          RevenuePotentialAtB      (farmers we can now serve at B)
        - RevenuePotentialLostAtA  (demand we abandon at the source)
        - RelocationCost           (mobilizing + distance)
        - OperatorTimeCost         (operator hours during the move)
        - OpportunityCost          (machine idle while in transit)

If NetBenefit clears a configurable threshold, a recommendation is created with
status 'pending'. The system NEVER relocates automatically - an operator must
approve or reject it (that workflow is the API in Step 2).

Explainable + deterministic + no ML. It stands on the earlier engines:
  - demand_engine.get_shortages()  -> where the shortages are
  - allocation_engine.recommend_machines() -> the best machine to bring in
    (already balances distance, idleness, and network efficiency)

Try it (from the backend/ folder):
    .venv\\Scripts\\python.exe -m app.services.relocation_engine
"""
from dataclasses import asdict, dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CHC, DemandRequest, Field, RelocationRecommendation
from app.services.allocation_engine import recommend_machines
from app.services.demand_engine import (
    MACHINE_TO_OPERATION,
    REQUESTS_PER_MACHINE,
    analyze_demand,
    build_clusters,
    get_shortages,
    nearest_cluster,
)


@dataclass(frozen=True)
class RelocationConfig:
    """All money/threshold knobs in one tunable place (rupees)."""

    revenue_per_job: float = 1200.0          # earned per farmer served
    operator_rate_per_hour: float = 150.0
    opportunity_rate_per_hour: float = 100.0
    avg_speed_kmph: float = 30.0             # farm-machinery road speed
    net_benefit_threshold: float = 500.0     # recommend only if NetBenefit exceeds this


DEFAULT_CONFIG = RelocationConfig()


@dataclass
class RelocationProposal:
    machine_id: int
    machine_type: str
    from_chc_id: int
    from_chc_name: str
    from_cluster: str
    to_cluster: str
    distance_km: float
    expected_farmers_served: int
    expected_revenue: float
    relocation_cost: float
    net_benefit: float
    breakdown: dict
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _representative_request(db: Session, centroids, cluster: str, operation: str) -> int | None:
    """A pending request of this operation that sits in the given cluster.

    We use it as the 'anchor' to ask the allocation engine which machine is best
    to bring into that cluster.
    """
    for req_id, lat, lon in db.execute(
        select(DemandRequest.id, Field.latitude, Field.longitude)
        .join(Field, Field.id == DemandRequest.field_id)
        .where(DemandRequest.operation_type == operation,
               DemandRequest.status == "pending")
        .order_by(DemandRequest.id)  # deterministic anchor -> reproducible demo
    ).all():
        if nearest_cluster(centroids, lat, lon) == cluster:
            return req_id
    return None


def evaluate_relocations(
    db: Session,
    config: RelocationConfig = DEFAULT_CONFIG,
    as_of: date | None = None,
) -> list[RelocationProposal]:
    """Compute (but do NOT persist) a NetBenefit proposal for each shortage."""
    today = as_of or date.today()
    insights = analyze_demand(db, as_of=today)
    demand_map = {(i.cluster, i.machine_type): i for i in insights}
    shortages = get_shortages(insights, min_risk="HIGH")
    centroids, chc_to_cluster = build_clusters(db)

    proposals: list[RelocationProposal] = []
    for s in shortages:
        operation = MACHINE_TO_OPERATION.get(s.machine_type)
        if not operation:
            continue
        anchor = _representative_request(db, centroids, s.cluster, operation)
        if anchor is None:
            continue

        # Ask the allocation engine which machine is best to bring in, then take
        # the top candidate that actually requires relocation (an external one).
        candidates = recommend_machines(db, anchor, top_n=5, as_of=today)
        best = next((c for c in (candidates or []) if c.relocation_required), None)
        if best is None:
            continue

        source_cluster = chc_to_cluster.get(best.chc_id, "?")

        # --- NetBenefit terms ---
        farmers = best.expected_farmers_served
        revenue_at_b = farmers * config.revenue_per_job

        # Revenue we give up at the source only matters if the source itself has
        # unmet demand for this machine type. An idle-surplus CHC loses nothing.
        src = demand_map.get((source_cluster, s.machine_type))
        src_unmet_jobs = max(0, src.expected_requests - src.available_supply * REQUESTS_PER_MACHINE) if src else 0
        revenue_lost_a = min(farmers, src_unmet_jobs) * config.revenue_per_job

        relocation_cost = best.relocation_cost
        travel_hours = best.distance_km / config.avg_speed_kmph
        operator_time_cost = travel_hours * config.operator_rate_per_hour
        opportunity_cost = travel_hours * config.opportunity_rate_per_hour

        net_benefit = (revenue_at_b - revenue_lost_a - relocation_cost
                       - operator_time_cost - opportunity_cost)

        breakdown = {
            "revenue_at_destination": round(revenue_at_b, 0),
            "revenue_lost_at_source": round(revenue_lost_a, 0),
            "relocation_cost": round(relocation_cost, 0),
            "operator_time_cost": round(operator_time_cost, 0),
            "opportunity_cost": round(opportunity_cost, 0),
            "config": asdict(config),
        }
        reason = (
            f"Move {s.machine_type} #{best.machine_id} from {best.chc_name} "
            f"({source_cluster}) to {s.cluster} to relieve a {s.risk_level} shortage. "
            f"Serves ~{farmers} farmers; net benefit Rs {net_benefit:.0f}."
        )

        proposals.append(RelocationProposal(
            machine_id=best.machine_id,
            machine_type=s.machine_type,
            from_chc_id=best.chc_id,
            from_chc_name=best.chc_name,
            from_cluster=source_cluster,
            to_cluster=s.cluster,
            distance_km=best.distance_km,
            expected_farmers_served=farmers,
            expected_revenue=round(revenue_at_b, 0),
            relocation_cost=round(relocation_cost, 0),
            net_benefit=round(net_benefit, 0),
            breakdown=breakdown,
            reason=reason,
        ))

    proposals.sort(key=lambda p: p.net_benefit, reverse=True)
    return proposals


def generate_recommendations(
    db: Session,
    config: RelocationConfig = DEFAULT_CONFIG,
    as_of: date | None = None,
) -> list[RelocationRecommendation]:
    """Persist a 'pending' recommendation for each proposal above the threshold.

    Idempotent: skips a proposal if an identical pending recommendation already
    exists (same machine -> same cluster).
    """
    created: list[RelocationRecommendation] = []
    for p in evaluate_relocations(db, config, as_of):
        if p.net_benefit <= config.net_benefit_threshold:
            continue
        existing = db.scalar(
            select(RelocationRecommendation).where(
                RelocationRecommendation.machine_id == p.machine_id,
                RelocationRecommendation.to_cluster == p.to_cluster,
                RelocationRecommendation.status == "pending",
            )
        )
        if existing:
            continue
        rec = RelocationRecommendation(
            machine_id=p.machine_id,
            from_chc_id=p.from_chc_id,
            to_cluster=p.to_cluster,
            machine_type=p.machine_type,
            net_benefit=p.net_benefit,
            relocation_cost=p.relocation_cost,
            expected_revenue=p.expected_revenue,
            expected_farmers_served=p.expected_farmers_served,
            status="pending",
            benefit_breakdown=p.breakdown,
        )
        db.add(rec)
        created.append(rec)
    db.commit()
    for rec in created:
        db.refresh(rec)
    return created


if __name__ == "__main__":
    from app.database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)  # ensure the table exists

    with SessionLocal() as session:
        proposals = evaluate_relocations(session)

        print(f"\n=== Relocation proposals evaluated: {len(proposals)} ===")
        for p in proposals:
            print(f"\n  Machine #{p.machine_id} ({p.machine_type})")
            print(f"    From: {p.from_chc_name} [{p.from_cluster}]  ->  To: {p.to_cluster}"
                  f"  ({p.distance_km:.0f} km)")
            print(f"    + revenue at destination : Rs {p.breakdown['revenue_at_destination']:.0f}"
                  f"  ({p.expected_farmers_served} farmers)")
            print(f"    - revenue lost at source : Rs {p.breakdown['revenue_lost_at_source']:.0f}")
            print(f"    - relocation cost        : Rs {p.breakdown['relocation_cost']:.0f}")
            print(f"    - operator time cost     : Rs {p.breakdown['operator_time_cost']:.0f}")
            print(f"    - opportunity cost       : Rs {p.breakdown['opportunity_cost']:.0f}")
            print(f"    = NET BENEFIT            : Rs {p.net_benefit:.0f}")

        created = generate_recommendations(session)
        print(f"\n=== Recommendations created (status=pending): {len(created)} ===")
        for r in created:
            print(f"  #{r.id}: move machine {r.machine_id} -> {r.to_cluster}, "
                  f"net benefit Rs {r.net_benefit:.0f}, status={r.status}")
