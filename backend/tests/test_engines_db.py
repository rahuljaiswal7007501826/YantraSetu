"""Engine tests against the seeded in-memory scenario."""
from sqlalchemy import update

from app.models import MachineAvailability, RelocationRecommendation
from app.services.allocation_engine import recommend_machines
from app.services.demand_engine import analyze_demand, get_shortages
from app.services.impact_engine import compute_impact
from app.services.relocation_engine import evaluate_relocations, generate_recommendations
from app.services.utilization_engine import compute_analytics


# --- Demand engine ---------------------------------------------------------
def test_demand_flags_south_combine_shortage(scenario, session):
    insights = analyze_demand(session)
    south = next(
        (i for i in insights if i.cluster == "South" and i.machine_type == "Combine Harvester"),
        None,
    )
    assert south is not None
    assert south.available_supply == 0
    assert south.risk_level == "CRITICAL"
    assert get_shortages(insights)  # at least one HIGH/CRITICAL shortage


def test_demand_supply_adjustment_relieves_shortage(scenario, session):
    # Crediting one combine to South should lower its shortage probability.
    base = {(i.cluster, i.machine_type): i for i in analyze_demand(session)}
    adjusted = {
        (i.cluster, i.machine_type): i
        for i in analyze_demand(session, supply_adjustments={("South", "Combine Harvester"): 1})
    }
    key = ("South", "Combine Harvester")
    assert adjusted[key].shortage_probability < base[key].shortage_probability


# --- Allocation engine -----------------------------------------------------
def test_allocation_picks_combine_and_needs_relocation(scenario, session):
    candidates = recommend_machines(session, scenario["request_ids"][0])
    assert candidates, "expected at least one candidate"
    top = candidates[0]
    assert top.machine_id == scenario["combine_id"]
    assert top.compatible is True
    assert top.relocation_required is True  # combine lives in North, field is South


def test_allocation_unknown_request_returns_none(scenario, session):
    assert recommend_machines(session, 999999) is None


# --- Relocation engine -----------------------------------------------------
def test_relocation_proposal_is_positive(scenario, session):
    proposals = evaluate_relocations(session)
    move = next((p for p in proposals if p.to_cluster == "South"), None)
    assert move is not None
    assert move.machine_id == scenario["combine_id"]
    assert move.from_chc_id == scenario["north_id"]
    assert move.net_benefit > 0
    # The financial breakdown carries all five explainable terms.
    for term in (
        "revenue_at_destination",
        "revenue_lost_at_source",
        "relocation_cost",
        "operator_time_cost",
        "opportunity_cost",
    ):
        assert term in move.breakdown


def test_generate_persists_pending_recommendation(scenario, session):
    created = generate_recommendations(session)
    assert len(created) >= 1
    assert all(r.status == "pending" for r in created)
    # Idempotent: running again creates no duplicates.
    assert generate_recommendations(session) == []


# --- Utilization engine ----------------------------------------------------
def test_utilization_computes_from_slots(scenario, session):
    a = compute_analytics(session)
    assert a.machines_counted == 2
    # combine 40h idle + tractor 40h booked -> 40 active / 80 schedulable = 50%.
    assert a.network_utilization_pct == 50.0
    assert a.demand_coverage_pct == 0.0  # all requests pending, none served
    assert 0 <= a.network_efficiency_score <= 100


def test_empty_network_nes_zero(session):
    a = compute_analytics(session)  # no scenario -> empty DB
    assert a.network_efficiency_score == 0.0
    assert a.machines_counted == 0


# --- Impact engine ---------------------------------------------------------
def test_impact_zero_relocations_before_equals_after(scenario, session):
    r = compute_impact(session)
    assert r.relocations_executed == 0
    assert r.before == r.after
    assert r.additional_farmers_served == 0
    assert r.net_benefit == 0


def test_impact_with_approved_relocation_shows_real_deltas(scenario, session):
    # Simulate the approve endpoint: combine goes in_transit + an approved record.
    session.execute(
        update(MachineAvailability)
        .where(MachineAvailability.machine_id == scenario["combine_id"])
        .values(status="in_transit")
    )
    session.add(RelocationRecommendation(
        machine_id=scenario["combine_id"], from_chc_id=scenario["north_id"],
        to_cluster="South", machine_type="Combine Harvester",
        net_benefit=3000.0, relocation_cost=1560.0, expected_revenue=6000.0,
        expected_farmers_served=5, status="approved", benefit_breakdown={},
    ))
    session.commit()

    r = compute_impact(session)
    assert r.relocations_executed == 1
    assert r.additional_farmers_served == 5
    assert r.revenue_gained == 6000.0
    assert r.net_benefit == 3000.0
    # Idle combine becomes active -> utilization rises.
    assert r.after.utilization_pct > r.before.utilization_pct
    # Crediting the combine to South relieves the shortage.
    assert r.critical_shortages_after < r.critical_shortages_before
    assert r.shortage_deltas
    d = r.shortage_deltas[0]
    assert d.cluster == "South" and d.machine_type == "Combine Harvester"
    assert d.shortage_probability_after < d.shortage_probability_before
