"""
Route Optimization Engine  (Phase 6, Step 2).

Single-vehicle Vehicle Routing Problem with Time Windows (VRPTW), solved with
Google OR-Tools. Given a machine's start point (depot) and a set of farmer stops
(each with a time window and a service duration), it returns the visiting order
that minimizes total travel while respecting the windows and the working day.

Independent of FastAPI and the database: it takes plain inputs and returns a
plain structured result, so it can be tested and reused anywhere.

Try it (from the backend/ folder):
    .venv\\Scripts\\python.exe -m app.services.route_engine
"""
from dataclasses import asdict, dataclass

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.utils.geo import haversine_km


@dataclass(frozen=True)
class RouteConfig:
    """Tunable knobs. Times are in minutes-since-midnight."""

    avg_speed_kmph: float = 30.0
    day_start_min: int = 8 * 60      # 08:00
    day_end_min: int = 18 * 60       # 18:00
    drop_penalty: int = 1_000_000    # >> any travel cost: only drop the infeasible
    time_limit_seconds: int = 3
    return_to_depot: bool = False


@dataclass(frozen=True)
class Stop:
    """One farmer field to visit."""

    stop_id: int
    lat: float
    lon: float
    open_min: int          # earliest service start (minutes since midnight)
    close_min: int         # latest service start
    service_min: int       # how long the operation takes


@dataclass
class RoutedStop:
    sequence: int
    stop_id: int | None    # None for the depot
    is_depot: bool
    lat: float
    lon: float
    arrival_min: int
    service_start_min: int
    service_end_min: int
    service_duration_min: int
    arrival_clock: str
    service_start_clock: str


@dataclass
class RouteResult:
    status: str
    feasible: bool
    ordered_stops: list[RoutedStop]
    visited_stop_ids: list[int]
    dropped_stop_ids: list[int]
    total_distance_km: float
    total_travel_time_min: int
    total_route_duration_min: int
    returned_to_depot: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def optimize_route(
    depot: tuple[float, float],
    stops: list[Stop],
    config: RouteConfig = RouteConfig(),
) -> RouteResult:
    """Solve the single-vehicle VRPTW and return the optimized route."""
    n = len(stops)
    if n == 0:
        return RouteResult("EMPTY", True, [], [], [], 0.0, 0, 0, config.return_to_depot)

    # Node layout: 0 = depot, 1..n = farmers, n+1 = dummy END (gives an open route).
    DEPOT, END, num_nodes = 0, n + 1, n + 2
    coords = [depot] + [(s.lat, s.lon) for s in stops] + [depot]  # END coords unused
    service = [0] + [s.service_min for s in stops] + [0]

    # Integer travel-time (minutes) matrix for the solver; float km matrix for reporting.
    travel_min = [[0] * num_nodes for _ in range(num_nodes)]
    dist_km = [[0.0] * num_nodes for _ in range(num_nodes)]
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i == j or i == END or j == END:
                continue  # any arc touching the dummy END is free (0)
            km = haversine_km(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            dist_km[i][j] = km
            travel_min[i][j] = int(round(km / config.avg_speed_kmph * 60))

    manager = pywrapcp.RoutingIndexManager(num_nodes, 1, [DEPOT], [END])
    routing = pywrapcp.RoutingModel(manager)

    # Objective = total TRAVEL time only (total service is constant, so it doesn't
    # change the optimal order; keeping it out makes the objective clean).
    def travel_cb(from_index, to_index):
        return travel_min[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    travel_idx = routing.RegisterTransitCallback(travel_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(travel_idx)

    # Time dimension transit = service at 'from' + travel 'from'->'to'.
    def time_cb(from_index, to_index):
        fn, tn = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        return service[fn] + travel_min[fn][tn]

    time_idx = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(
        time_idx,
        config.day_end_min,   # slack: allow waiting for a window to open
        config.day_end_min,   # horizon: cumulative time cannot exceed end of day
        False,                # start cumul not fixed to 0 (the day starts at 08:00)
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    # Time windows: depot/end within the working day, each farmer within its window.
    time_dim.CumulVar(routing.Start(0)).SetRange(config.day_start_min, config.day_end_min)
    time_dim.CumulVar(routing.End(0)).SetRange(config.day_start_min, config.day_end_min)
    for k, s in enumerate(stops, start=1):
        time_dim.CumulVar(manager.NodeToIndex(k)).SetRange(s.open_min, s.close_min)

    # Every farmer stop is droppable, but only at a heavy penalty.
    for k in range(1, n + 1):
        routing.AddDisjunction([manager.NodeToIndex(k)], config.drop_penalty)

    # Deterministic search settings.
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromSeconds(config.time_limit_seconds)
    params.log_search = False

    solution = routing.SolveWithParameters(params)
    if solution is None:
        return RouteResult("NO_SOLUTION", False, [], [],
                           [s.stop_id for s in stops], 0.0, 0, 0, config.return_to_depot)

    # Walk the chosen route from the depot to the end.
    ordered: list[RoutedStop] = []
    visited_ids: list[int] = []
    total_distance = 0.0
    total_travel = 0
    idx = routing.Start(0)
    prev_node = None
    prev_departure = 0
    depot_departure = solution.Min(time_dim.CumulVar(idx))
    last_service_end = depot_departure
    seq = 0
    while not routing.IsEnd(idx):
        node = manager.IndexToNode(idx)
        cumul = solution.Min(time_dim.CumulVar(idx))  # service start (respects window + waiting)
        if prev_node is None:
            arrival = service_start = service_end = cumul  # depot: 0 service
        else:
            travel = travel_min[prev_node][node]
            arrival = prev_departure + travel
            service_start = cumul
            service_end = service_start + service[node]
            total_travel += travel
            total_distance += dist_km[prev_node][node]

        is_depot = node == DEPOT
        sid = None if is_depot else stops[node - 1].stop_id
        if not is_depot:
            visited_ids.append(sid)
        ordered.append(RoutedStop(
            sequence=seq, stop_id=sid, is_depot=is_depot,
            lat=coords[node][0], lon=coords[node][1],
            arrival_min=arrival, service_start_min=service_start,
            service_end_min=service_end, service_duration_min=service[node],
            arrival_clock=_clock(arrival), service_start_clock=_clock(service_start),
        ))
        last_service_end = service_end
        prev_node, prev_departure = node, service_end
        seq += 1
        idx = solution.Value(routing.NextVar(idx))

    dropped = [
        stops[k - 1].stop_id
        for k in range(1, n + 1)
        if solution.Value(routing.NextVar(manager.NodeToIndex(k))) == manager.NodeToIndex(k)
    ]

    return RouteResult(
        status="SOLVED",
        feasible=True,
        ordered_stops=ordered,
        visited_stop_ids=visited_ids,
        dropped_stop_ids=dropped,
        total_distance_km=round(total_distance, 2),
        total_travel_time_min=total_travel,
        total_route_duration_min=last_service_end - depot_departure,
        returned_to_depot=config.return_to_depot,
    )


if __name__ == "__main__":
    # Deterministic Cluster B demo: 5 harvesting stops, one with an impossible
    # time window (F105) so we can see it dropped.
    depot = (26.50, 80.95)  # machine's entry point into Cluster B
    stops = [
        Stop(101, 26.52, 80.97, open_min=8 * 60,      close_min=12 * 60, service_min=60),
        Stop(102, 26.48, 80.93, open_min=9 * 60,      close_min=14 * 60, service_min=90),
        Stop(103, 26.55, 80.99, open_min=8 * 60 + 30, close_min=16 * 60, service_min=60),
        Stop(104, 26.45, 80.90, open_min=10 * 60,     close_min=17 * 60, service_min=75),
        Stop(105, 26.60, 81.05, open_min=8 * 60,      close_min=8 * 60 + 10, service_min=60),  # impossible
    ]

    result = optimize_route(depot, stops)
    rerun = optimize_route(depot, stops)
    deterministic = (
        [s.stop_id for s in result.ordered_stops] == [s.stop_id for s in rerun.ordered_stops]
        and result.dropped_stop_ids == rerun.dropped_stop_ids
        and result.total_distance_km == rerun.total_distance_km
    )

    print("=== Route Optimization (Cluster B demo) ===")
    print(f"status={result.status}  feasible={result.feasible}")
    arrow = " -> ".join("Depot" if s.is_depot else f"F{s.stop_id}" for s in result.ordered_stops)
    print(f"\nRoute: {arrow}")
    print(f"\n{'SEQ':>3} {'STOP':>6} {'ARRIVE':>7} {'START':>7} {'END':>7} {'SERVICE':>8}")
    for s in result.ordered_stops:
        label = "DEPOT" if s.is_depot else f"F{s.stop_id}"
        print(f"{s.sequence:>3} {label:>6} {s.arrival_clock:>7} {s.service_start_clock:>7} "
              f"{_clock(s.service_end_min):>7} {s.service_duration_min:>6}m")
    print(f"\n  visited : {result.visited_stop_ids}")
    print(f"  dropped : {result.dropped_stop_ids}")
    print(f"  total distance      : {result.total_distance_km} km")
    print(f"  total travel time   : {result.total_travel_time_min} min")
    print(f"  total route duration: {result.total_route_duration_min} min")
    print(f"  returned to depot   : {result.returned_to_depot}")
    print(f"  deterministic re-run: {deterministic}")
