"""
Intelligent Allocation Engine  (Phase 4, Step 1).

Two parts, both explainable and deterministic (no ML):

1. COMPATIBILITY ENGINE (a HARD gate)
   A compatibility matrix maps each operation to the machine types that can
   perform it. Incompatible machines are removed *before* any scoring - a
   sprayer will never be offered for a harvesting job.

2. ALLOCATION SCORING (weighted, 0-100)
   For every compatible + available machine we compute:

     AllocationScore = 100 * (
         w1*distance + w2*urgency + w3*compatibility + w4*capacity_fit
       + w5*relocation_cost + w6*cluster_efficiency_gain + w7*future_demand_avoidance )

   Weights are configurable (AllocationWeights). Each candidate carries its
   factor breakdown, distance, relocation cost, expected farmers served, and a
   plain-English reason.

It builds on the demand engine: it reuses the same clusters and asks the demand
engine how risky the destination is (that powers "future_demand_avoidance" and
"expected_farmers_served").

Try it (from the backend/ folder):
    .venv\\Scripts\\python.exe -m app.services.allocation_engine
"""
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CHC, DemandRequest, Field, Machine, MachineAvailability
from app.services.demand_engine import (
    FORECAST_DAYS,
    analyze_demand,
    build_clusters,
    nearest_cluster,
)
from app.utils.geo import haversine_km

# --------------------------------------------------------------------------
# 1. Compatibility matrix - the HARD gate. Primary type first in each list.
# --------------------------------------------------------------------------
COMPATIBILITY: dict[str, list[str]] = {
    "Harvesting": ["Combine Harvester"],
    "Ploughing": ["Tractor"],
    "Tillage": ["Rotavator", "Tractor"],
    "Sowing": ["Seed Drill"],
    "Spraying": ["Sprayer"],
    "Baling": ["Baler"],
}


def is_compatible(operation: str, machine_type: str) -> bool:
    """Hard constraint: can this machine type perform this operation at all?"""
    return machine_type in COMPATIBILITY.get(operation, [])


def compatible_types(operation: str) -> list[str]:
    return COMPATIBILITY.get(operation, [])


# --------------------------------------------------------------------------
# 2. Scoring configuration - all tunable in one place.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class AllocationWeights:
    """Weights for the seven allocation factors. Must sum to 1.0."""

    distance: float = 0.25
    urgency: float = 0.15
    compatibility: float = 0.10
    capacity_fit: float = 0.10
    relocation_cost: float = 0.15
    cluster_efficiency_gain: float = 0.15
    future_demand_avoidance: float = 0.10


DEFAULT_WEIGHTS = AllocationWeights()

URGENCY_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.3}
RISK_SCORE = {"CRITICAL": 1.0, "HIGH": 0.8, "MEDIUM": 0.5, "LOW": 0.3}

DISTANCE_MAX_KM = 150.0        # beyond this the distance score bottoms out at 0
CAPACITY_REFERENCE = 3.0       # a machine at/above this capacity fits fully
RELOCATION_BASE_FEE = 500.0    # rupees: fixed mobilization cost
RELOCATION_PER_KM = 20.0       # rupees per km to move a machine
RELOCATION_COST_REFERENCE = 3000.0  # rupees: normalizes the relocation-cost score
MACHINE_WINDOW_CAPACITY = 5    # farmers one machine can serve in the horizon


@dataclass
class MachineCandidate:
    machine_id: int
    machine_type: str
    chc_id: int
    chc_name: str
    score: float                  # 0-100
    distance_km: float
    compatible: bool              # always True here (incompatible are gated out)
    relocation_required: bool
    relocation_cost: float        # rupees
    expected_farmers_served: int
    reason: str
    factors: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _idle_ratios(db: Session, today: date, window_end: date) -> dict[int, float]:
    """For each machine, the fraction of its slots in the window that are 'available'."""
    total: dict[int, int] = defaultdict(int)
    avail: dict[int, int] = defaultdict(int)
    for mid, status in db.execute(
        select(MachineAvailability.machine_id, MachineAvailability.status)
        .where(MachineAvailability.date >= today, MachineAvailability.date < window_end)
    ).all():
        total[mid] += 1
        if status == "available":
            avail[mid] += 1
    return {mid: avail[mid] / total[mid] for mid in total}


def recommend_machines(
    db: Session,
    request_id: int,
    weights: AllocationWeights = DEFAULT_WEIGHTS,
    top_n: int = 5,
    as_of: date | None = None,
) -> list[MachineCandidate] | None:
    """Return ranked, compatible machine candidates for a demand request.

    Returns None if the request id doesn't exist (the router turns that into 404).
    """
    today = as_of or date.today()
    window_end = today + timedelta(days=FORECAST_DAYS)

    request = db.get(DemandRequest, request_id)
    if request is None:
        return None
    plot = db.get(Field, request.field_id)

    allowed_types = compatible_types(request.operation_type)
    if not allowed_types:
        return []  # unknown operation -> nothing is compatible

    # Clusters + demand picture (reused from the demand engine).
    centroids, chc_to_cluster = build_clusters(db)
    field_cluster = nearest_cluster(centroids, plot.latitude, plot.longitude)
    demand_map = {
        (i.cluster, i.machine_type): i for i in analyze_demand(db, as_of=today)
    }

    idle_ratio = _idle_ratios(db, today, window_end)
    idle_machine_ids = {mid for mid, r in idle_ratio.items() if r > 0}
    chc_by_id = {c.id: c for c in db.scalars(select(CHC)).all()}

    # HARD GATE: only operational machines of a compatible type that have some
    # availability in the window are even considered.
    machines = db.scalars(
        select(Machine).where(
            Machine.machine_type.in_(allowed_types),
            Machine.maintenance_status == "operational",
        )
    ).all()

    candidates: list[MachineCandidate] = []
    for m in machines:
        if m.id not in idle_machine_ids:
            continue  # fully booked / under maintenance -> can't serve

        chc = chc_by_id.get(m.chc_id)
        machine_cluster = chc_to_cluster.get(m.chc_id)
        distance = haversine_km(m.current_latitude, m.current_longitude,
                                plot.latitude, plot.longitude)

        # --- the seven factors (each 0-1) ---
        distance_score = max(0.0, 1 - distance / DISTANCE_MAX_KM)
        urgency_score = URGENCY_SCORE.get(request.urgency, 0.6)
        compatibility_score = 1.0 if m.machine_type == allowed_types[0] else 0.85
        capacity_fit = min(1.0, m.capacity / CAPACITY_REFERENCE)

        relocation_required = machine_cluster != field_cluster
        relocation_cost = (
            RELOCATION_BASE_FEE + distance * RELOCATION_PER_KM
            if relocation_required else 0.0
        )
        relocation_cost_score = max(0.0, 1 - relocation_cost / RELOCATION_COST_REFERENCE)

        cluster_efficiency_gain = idle_ratio.get(m.id, 0.0)  # using idle assets = gain

        insight = demand_map.get((field_cluster, m.machine_type))
        dest_risk = insight.risk_level if insight else "LOW"
        future_demand_avoidance = RISK_SCORE.get(dest_risk, 0.3)

        score = 100.0 * (
            weights.distance * distance_score
            + weights.urgency * urgency_score
            + weights.compatibility * compatibility_score
            + weights.capacity_fit * capacity_fit
            + weights.relocation_cost * relocation_cost_score
            + weights.cluster_efficiency_gain * cluster_efficiency_gain
            + weights.future_demand_avoidance * future_demand_avoidance
        )

        expected_here = insight.expected_requests if insight else 1
        expected_farmers_served = max(1, min(expected_here, MACHINE_WINDOW_CAPACITY))

        reason = _build_reason(
            m, chc, distance, relocation_required, relocation_cost,
            cluster_efficiency_gain, dest_risk, field_cluster, expected_farmers_served,
        )

        candidates.append(MachineCandidate(
            machine_id=m.id,
            machine_type=m.machine_type,
            chc_id=m.chc_id,
            chc_name=chc.name if chc else "",
            score=round(score, 1),
            distance_km=round(distance, 1),
            compatible=True,
            relocation_required=relocation_required,
            relocation_cost=round(relocation_cost, 0),
            expected_farmers_served=expected_farmers_served,
            reason=reason,
            factors={
                "distance_score": round(distance_score, 2),
                "urgency_score": round(urgency_score, 2),
                "compatibility_score": round(compatibility_score, 2),
                "capacity_fit": round(capacity_fit, 2),
                "relocation_cost_score": round(relocation_cost_score, 2),
                "cluster_efficiency_gain": round(cluster_efficiency_gain, 2),
                "future_demand_avoidance": round(future_demand_avoidance, 2),
                "weights": asdict(weights),
            },
        ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_n]


def _build_reason(machine, chc, distance, relocation_required, relocation_cost,
                  idle_ratio, dest_risk, field_cluster, expected_farmers) -> str:
    parts = [f"{machine.machine_type} from {chc.name if chc else 'CHC'} "
             f"({distance:.0f} km away)."]
    if idle_ratio >= 0.7:
        parts.append("Currently idle.")
    if relocation_required:
        parts.append(f"Needs relocation (~Rs {relocation_cost:.0f}).")
    else:
        parts.append("Already local, no relocation needed.")
    if dest_risk in ("HIGH", "CRITICAL"):
        parts.append(f"Helps relieve a {dest_risk} shortage in {field_cluster}.")
    parts.append(f"Can serve ~{expected_farmers} nearby farmers.")
    return " ".join(parts)


if __name__ == "__main__":
    from app.database import SessionLocal

    with SessionLocal() as session:
        # Pick a pending harvesting request (the Cluster B shortage) to demonstrate.
        req = session.scalars(
            select(DemandRequest).where(
                DemandRequest.operation_type == "Harvesting",
                DemandRequest.status == "pending",
            ).limit(1)
        ).first()
        if req is None:
            print("No pending harvesting request found - run seed_database.py first.")
            raise SystemExit(1)

        plot = session.get(Field, req.field_id)
        print(f"Request #{req.id}: {req.operation_type} on field #{plot.id} "
              f"(crop {plot.crop_type}, urgency {req.urgency})")

        # Show the hard gate at work.
        total_ops = session.scalar(
            select(__import__("sqlalchemy").func.count(Machine.id))
            .where(Machine.maintenance_status == "operational")
        )
        allowed = compatible_types(req.operation_type)
        n_compat = session.scalar(
            select(__import__("sqlalchemy").func.count(Machine.id))
            .where(Machine.machine_type.in_(allowed))
        )
        print(f"Compatibility gate: operation needs {allowed}; "
              f"{n_compat} of {total_ops} machines are a compatible type "
              f"(the rest are eliminated before scoring).")

        results = recommend_machines(session, req.id, top_n=5)

    print("\n=== Ranked machine candidates ===")
    print(f"{'MACHINE':>8}  {'TYPE':<18}{'CHC':<22}{'SCORE':>6}{'DIST':>7}{'RELOC?':>7}{'COST':>8}{'FARMERS':>8}")
    for c in results:
        print(f"{c.machine_id:>8}  {c.machine_type:<18}{c.chc_name:<22}{c.score:>6}"
              f"{c.distance_km:>6}k{'yes' if c.relocation_required else 'no':>7}"
              f"{c.relocation_cost:>8.0f}{c.expected_farmers_served:>8}")

    if results:
        top = results[0]
        print(f"\n=== Top recommendation: machine #{top.machine_id} (score {top.score}) ===")
        print(f"    {top.reason}")
        print("    factor breakdown:")
        for name, value in top.factors.items():
            if name != "weights":
                print(f"      {name}: {value}")
