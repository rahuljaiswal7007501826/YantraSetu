"""
Demand Intelligence Engine  (Phase 3, Step 1).

Explainable + deterministic. NO machine learning, NO black box. It reads the
existing database and, for every (cluster, machine_type) that has demand,
computes a transparent demand picture:

    DemandScore (0-100) = weighted sum of four normalized factors
        historical    - completed requests in the recent past (baseline demand)
        crop_calendar - is this the season for that operation?
        live_request  - how many requests are pending right now
        momentum      - how many of those are urgent / due very soon

    expected_requests   = pending now + a projection from historical rate
    available_supply    = idle, operational machines of that type in the cluster
    shortage_probability = how far expected demand outstrips serviceable supply
    risk_level          = LOW / MEDIUM / HIGH / CRITICAL (from shortage prob + volume)

Every number is reproducible from the same data, and each insight carries its
factor breakdown so a human (or a judge) can see *why* it was flagged.

Clusters are groups of nearby CHCs (we use the CHC.location label); each demand
request is attributed to the nearest cluster centroid by its field location.

Try it (from the backend/ folder):
    .venv\\Scripts\\python.exe -m app.services.demand_engine
"""
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CHC, DemandRequest, Field, Machine, MachineAvailability
from app.utils.geo import haversine_km


# --------------------------------------------------------------------------
# Configuration - explainable and tunable in one place.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class DemandWeights:
    """Weights for the four demand factors. Must sum to 1.0."""

    historical: float = 0.20
    crop_calendar: float = 0.15
    live_request: float = 0.45   # current pending demand dominates
    momentum: float = 0.20


DEFAULT_WEIGHTS = DemandWeights()

# Which machine type performs which operation (refined into a full compatibility
# matrix in Phase 4). Used to line demand (by operation) up against supply (by type).
OPERATION_TO_MACHINE = {
    "Harvesting": "Combine Harvester",
    "Ploughing": "Tractor",
    "Tillage": "Rotavator",
    "Sowing": "Seed Drill",
    "Spraying": "Sprayer",
    "Baling": "Baler",
}
MACHINE_TO_OPERATION = {v: k for k, v in OPERATION_TO_MACHINE.items()}

# Simple crop/season calendar: peak months per operation (1=Jan .. 12=Dec).
PEAK_MONTHS = {
    "Harvesting": {3, 4, 10, 11},
    "Ploughing": {5, 6, 11, 12},
    "Tillage": {5, 6, 10, 11},
    "Sowing": {6, 7, 11, 12},
    "Spraying": {7, 8, 12, 1},
}

HIST_WINDOW_DAYS = 30      # how far back "historical" looks
HIST_REFERENCE = 15        # this many historical requests -> full historical score
LIVE_REFERENCE = 10        # this many pending requests -> full live/momentum score
FORECAST_DAYS = 7          # planning horizon for supply + projection
REQUESTS_PER_MACHINE = 5   # jobs one machine can realistically serve in the horizon
SOON_DAYS = 3              # a request due within this many days counts as "urgent"


def _risk_level(shortage_probability: float, expected_requests: int) -> str:
    """Risk = how likely a shortage is (probability) AND how big it is (volume).

    A high probability on a trivial amount of demand is not "critical"; a large
    body of unmet requests is. Gating by volume keeps the output meaningful, so a
    cluster with 1 unmet request doesn't rank alongside one with 25.
    """
    if shortage_probability >= 0.60 and expected_requests >= 10:
        return "CRITICAL"
    if shortage_probability >= 0.50 and expected_requests >= 5:
        return "HIGH"
    if shortage_probability >= 0.25 and expected_requests >= 1:
        return "MEDIUM"
    return "LOW"


def _calendar_score(operation: str, month: int) -> float:
    """1.0 in peak season, 0.6 in an adjacent month, 0.3 off-season."""
    peaks = PEAK_MONTHS.get(operation, set())
    if not peaks:
        return 0.5
    if month in peaks:
        return 1.0
    # month distance on a 12-month circle
    if any(min((month - p) % 12, (p - month) % 12) == 1 for p in peaks):
        return 0.6
    return 0.3


@dataclass
class DemandInsight:
    cluster: str
    machine_type: str
    demand_score: float           # 0-100
    risk_level: str               # LOW / MEDIUM / HIGH / CRITICAL
    expected_requests: int
    available_supply: int         # idle operational machines of this type
    shortage_probability: float   # 0-1
    reason: str
    factors: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def build_clusters(db: Session):
    """Group CHCs into clusters by their location label; return centroids + map.

    Public so other engines (allocation, relocation) can reuse the same notion of
    "cluster" instead of re-implementing it.
    Returns (centroids: {cluster -> (lat, lon)}, chc_to_cluster: {chc_id -> cluster}).
    """
    rows = db.execute(
        select(CHC.id, CHC.location, CHC.latitude, CHC.longitude)
    ).all()
    lats: dict[str, list[float]] = defaultdict(list)
    lons: dict[str, list[float]] = defaultdict(list)
    chc_to_cluster: dict[int, str] = {}
    for chc_id, location, lat, lon in rows:
        lats[location].append(lat)
        lons[location].append(lon)
        chc_to_cluster[chc_id] = location
    centroids = {
        loc: (sum(lats[loc]) / len(lats[loc]), sum(lons[loc]) / len(lons[loc]))
        for loc in lats
    }
    return centroids, chc_to_cluster


def nearest_cluster(centroids: dict[str, tuple[float, float]], lat: float, lon: float) -> str:
    """Return the cluster label whose centroid is closest to the given point."""
    return min(centroids, key=lambda c: haversine_km(lat, lon, *centroids[c]))


def analyze_demand(
    db: Session,
    weights: DemandWeights = DEFAULT_WEIGHTS,
    as_of: date | None = None,
    supply_adjustments: dict[tuple[str, str], int] | None = None,
) -> list[DemandInsight]:
    """Compute demand insights for every (cluster, machine_type) with demand.

    `supply_adjustments` optionally adds (or removes) machines of supply for a
    given (cluster, machine_type) before scoring. It is a hypothetical hook used
    by the impact engine to model BEFORE/AFTER relocation scenarios; it defaults
    to None so normal callers behave exactly as before.
    """
    today = as_of or date.today()
    window_end = today + timedelta(days=FORECAST_DAYS)
    hist_start = today - timedelta(days=HIST_WINDOW_DAYS)

    centroids, chc_to_cluster = build_clusters(db)

    # --- Supply: idle, operational machines with an available slot in the window ---
    idle_machine_ids = set(
        db.scalars(
            select(MachineAvailability.machine_id)
            .where(
                MachineAvailability.status == "available",
                MachineAvailability.date >= today,
                MachineAvailability.date < window_end,
            )
            .distinct()
        ).all()
    )
    supply: dict[tuple[str, str], int] = defaultdict(int)
    for mid, chc_id, mtype, mstatus in db.execute(
        select(Machine.id, Machine.chc_id, Machine.machine_type, Machine.maintenance_status)
    ).all():
        cluster = chc_to_cluster.get(chc_id)
        if cluster and mstatus == "operational" and mid in idle_machine_ids:
            supply[(cluster, mtype)] += 1

    # Hypothetical supply overrides (impact engine: model a machine idle at its
    # source cluster vs. serving its destination cluster). No-op for normal callers.
    if supply_adjustments:
        for adj_key, delta in supply_adjustments.items():
            supply[adj_key] += delta

    # --- Demand: pending (live) and completed (historical), attributed to clusters ---
    pending = defaultdict(int)
    urgent = defaultdict(int)
    for op, urgency, req_date, lat, lon in db.execute(
        select(
            DemandRequest.operation_type, DemandRequest.urgency,
            DemandRequest.requested_date, Field.latitude, Field.longitude,
        ).join(Field, Field.id == DemandRequest.field_id)
        .where(DemandRequest.status == "pending")
    ).all():
        mtype = OPERATION_TO_MACHINE.get(op)
        if not mtype:
            continue
        key = (nearest_cluster(centroids, lat, lon), mtype)
        pending[key] += 1
        if urgency == "high" or (req_date - today).days <= SOON_DAYS:
            urgent[key] += 1

    historical = defaultdict(int)
    for op, lat, lon in db.execute(
        select(DemandRequest.operation_type, Field.latitude, Field.longitude)
        .join(Field, Field.id == DemandRequest.field_id)
        .where(DemandRequest.status == "completed",
               DemandRequest.requested_date >= hist_start)
    ).all():
        mtype = OPERATION_TO_MACHINE.get(op)
        if not mtype:
            continue
        historical[(nearest_cluster(centroids, lat, lon), mtype)] += 1

    # --- Score every (cluster, machine_type) that shows any demand ---
    insights: list[DemandInsight] = []
    keys = set(pending) | set(historical)
    for cluster, mtype in keys:
        key = (cluster, mtype)
        operation = MACHINE_TO_OPERATION.get(mtype, "")
        n_pending = pending.get(key, 0)
        n_urgent = urgent.get(key, 0)
        n_hist = historical.get(key, 0)

        historical_score = min(1.0, n_hist / HIST_REFERENCE)
        live_score = min(1.0, n_pending / LIVE_REFERENCE)
        momentum_score = min(1.0, n_urgent / LIVE_REFERENCE)
        calendar_score = _calendar_score(operation, today.month)

        demand_score = 100.0 * (
            weights.historical * historical_score
            + weights.crop_calendar * calendar_score
            + weights.live_request * live_score
            + weights.momentum * momentum_score
        )

        projected_new = round((n_hist / HIST_WINDOW_DAYS) * FORECAST_DAYS)
        expected = n_pending + projected_new
        available = supply.get(key, 0)
        serviceable = available * REQUESTS_PER_MACHINE
        shortage_prob = 0.0 if expected <= 0 else max(0.0, min(0.98, 1 - serviceable / expected))
        risk = _risk_level(shortage_prob, expected)

        reason = (
            f"{mtype} demand in {cluster} is {risk}. "
            f"Expected requests: {expected}, available machines: {available}, "
            f"shortage probability: {shortage_prob * 100:.0f}%."
        )

        insights.append(DemandInsight(
            cluster=cluster,
            machine_type=mtype,
            demand_score=round(demand_score, 1),
            risk_level=risk,
            expected_requests=expected,
            available_supply=available,
            shortage_probability=round(shortage_prob, 2),
            reason=reason,
            factors={
                "historical_score": round(historical_score, 2),
                "crop_calendar_score": round(calendar_score, 2),
                "live_request_score": round(live_score, 2),
                "momentum_score": round(momentum_score, 2),
                "pending_requests": n_pending,
                "historical_requests": n_hist,
                "weights": asdict(weights),
            },
        ))

    insights.sort(key=lambda i: (i.shortage_probability, i.demand_score), reverse=True)
    return insights


def get_shortages(insights: list[DemandInsight], min_risk: str = "HIGH") -> list[DemandInsight]:
    """Filter to the risky ones (HIGH/CRITICAL by default)."""
    allowed = {"CRITICAL"} if min_risk == "CRITICAL" else {"HIGH", "CRITICAL"}
    return [i for i in insights if i.risk_level in allowed]


if __name__ == "__main__":
    from app.database import SessionLocal

    with SessionLocal() as session:
        results = analyze_demand(session)

    print("\n=== Demand Intelligence (top pairs by shortage risk) ===")
    print(f"{'CLUSTER':<12}{'MACHINE TYPE':<20}{'SCORE':>6}{'RISK':>10}"
          f"{'EXP':>5}{'SUPPLY':>7}{'SHORTAGE':>10}")
    for i in results[:10]:
        print(f"{i.cluster:<12}{i.machine_type:<20}{i.demand_score:>6}{i.risk_level:>10}"
              f"{i.expected_requests:>5}{i.available_supply:>7}{i.shortage_probability*100:>9.0f}%")

    shortages = get_shortages(results)
    print(f"\n=== Shortage / high-risk areas: {len(shortages)} ===")
    for s in shortages:
        print(f"  [{s.risk_level}] {s.reason}")

    if shortages:
        top = shortages[0]
        print(f"\n=== Why '{top.cluster} / {top.machine_type}' was flagged ===")
        for name, value in top.factors.items():
            if name != "weights":
                print(f"    {name}: {value}")
