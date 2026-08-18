"""Pure OR-Tools route engine tests (no database)."""
from app.services.route_engine import RouteConfig, Stop, optimize_route

DEPOT = (26.50, 80.95)


def _stops():
    # Four reachable stops with generous windows.
    return [
        Stop(101, 26.52, 80.97, open_min=8 * 60, close_min=16 * 60, service_min=60),
        Stop(102, 26.48, 80.93, open_min=8 * 60, close_min=16 * 60, service_min=60),
        Stop(103, 26.55, 80.99, open_min=8 * 60, close_min=16 * 60, service_min=60),
        Stop(104, 26.45, 80.90, open_min=8 * 60, close_min=16 * 60, service_min=60),
    ]


def test_route_solves_and_visits_all_feasible():
    r = optimize_route(DEPOT, _stops())
    assert r.status == "SOLVED"
    assert r.feasible is True
    assert set(r.visited_stop_ids) == {101, 102, 103, 104}
    assert r.dropped_stop_ids == []
    # First stop is always the depot.
    assert r.ordered_stops[0].is_depot is True
    # Arrival times are non-decreasing along the plan.
    arrivals = [s.arrival_min for s in r.ordered_stops]
    assert arrivals == sorted(arrivals)
    assert r.total_distance_km > 0


def test_route_is_deterministic():
    a = optimize_route(DEPOT, _stops())
    b = optimize_route(DEPOT, _stops())
    assert [s.stop_id for s in a.ordered_stops] == [s.stop_id for s in b.ordered_stops]
    assert a.total_distance_km == b.total_distance_km
    assert a.dropped_stop_ids == b.dropped_stop_ids


def test_route_drops_infeasible_time_window():
    stops = _stops() + [
        # Far away with an impossible early window -> cannot be served in time.
        Stop(999, 27.60, 81.80, open_min=8 * 60, close_min=8 * 60 + 5, service_min=60),
    ]
    r = optimize_route(DEPOT, stops)
    assert 999 in r.dropped_stop_ids
    assert 999 not in r.visited_stop_ids


def test_route_empty_input():
    r = optimize_route(DEPOT, [])
    assert r.status == "EMPTY"
    assert r.ordered_stops == []
    assert r.total_distance_km == 0.0


def test_route_single_stop():
    r = optimize_route(DEPOT, [_stops()[0]])
    assert r.status == "SOLVED"
    assert r.visited_stop_ids == [101]
