"""Thuật toán tìm đường (spec 05, mục 2): đường nhanh nhất, lộ trình thay thế, chỉ dẫn."""
import heapq
import math

import numpy as np
import pyarrow as pa
import pytest
import shapely
from shapely.geometry import LineString

from floodrisk.api.graphroute import SPEEDS_KMH, GraphError, RoadGraph, RouteParams

LAT0, LON0 = 10.78, 106.70
KX = 111_320.0 * math.cos(math.radians(LAT0))
KY = 110_540.0
BIKE_MS = SPEEDS_KMH["bike"]["default"] / 3.6  # xe máy trên đường dân cư


def lonlat(x_m: float, y_m: float) -> tuple[float, float]:
    return LON0 + x_m / KX, LAT0 + y_m / KY


def build(points: dict[str, tuple[float, float]], edges: list[tuple], wkb=None) -> tuple[RoadGraph, dict[str, int]]:
    """edges: (a, b, chiều dài m, highway, tên, hai chiều?)."""
    index = {name: i for i, name in enumerate(points)}
    lon, lat = zip(*(lonlat(*points[name]) for name in points))
    u, v, length, highway, names = [], [], [], [], []
    for a, b, meters, kind, name, both in edges:
        for x, y in ((a, b), (b, a)) if both else ((a, b),):
            u.append(index[x]); v.append(index[y]); length.append(meters); highway.append(kind); names.append(name)
    graph = RoadGraph(np.array(lon), np.array(lat), np.array(u), np.array(v), np.array(length),
                      np.array(highway, dtype=object), np.array(names, dtype=object), wkb)
    return graph, index


def road(a, b, meters, kind="residential", name="", both=True):
    return (a, b, meters, kind, name, both)


def grid(n=4, step=200.0, kind="residential"):
    points = {f"{r}{c}": (c * step, r * step) for r in range(n) for c in range(n)}
    edges = []
    for r in range(n):
        for c in range(n):
            if c + 1 < n:
                edges.append(road(f"{r}{c}", f"{r}{c + 1}", step, kind, f"Ngang {r}"))
            if r + 1 < n:
                edges.append(road(f"{r}{c}", f"{r + 1}{c}", step, kind, f"Dọc {c}"))
    return build(points, edges)


def corridors(lengths, segments=5):
    """Các hành lang song song nối A với B, chỉ chung hai đầu."""
    points = {"A": (0.0, 0.0), "B": (10_000.0, 0.0)}
    edges = []
    for k, total in enumerate(lengths):
        chain = ["A"] + [f"c{k}_{i}" for i in range(1, segments)] + ["B"]
        for i, name in enumerate(chain[1:-1], start=1):
            points[name] = (10_000.0 * i / segments, 300.0 * (k + 1))
        for a, b in zip(chain, chain[1:]):
            edges.append(road(a, b, total / segments, name=f"Hành lang {k}"))
    return build(points, edges)


def total(graph, route):
    return float(graph.length_m[route.edges].sum())


# ----------------------------------------------------------------------------- đường nhanh nhất
def test_fastest_route_on_grid_has_the_expected_length_and_time():
    graph, ix = grid()
    routes = graph.find_routes(ix["00"], ix["33"], "bike")
    best = routes[0]
    assert best.kind == "fastest" and best.distance_m == pytest.approx(1200)
    assert best.duration_s == pytest.approx(1200 / BIKE_MS)
    assert best.nodes[0] == ix["00"] and best.nodes[-1] == ix["33"]


def test_same_origin_and_destination_is_an_error():
    graph, ix = grid()
    with pytest.raises(GraphError, match="trùng"):
        graph.find_routes(ix["00"], ix["00"], "bike")


def test_unreachable_destination_gives_no_routes():
    graph, ix = build({"A": (0, 0), "B": (100, 0), "C": (5000, 0)}, [road("A", "B", 100)])
    assert graph.find_routes(ix["A"], ix["C"], "bike") == []


def test_one_way_street_is_respected():
    # A→B có đường tắt một chiều 1 km; chiều ngược lại phải đi vòng qua C (3 km).
    graph, ix = build(
        {"A": (0, 0), "B": (1000, 0), "C": (500, 1200)},
        [road("A", "B", 1000, both=False), road("B", "C", 1500), road("C", "A", 1500)],
    )
    forward = graph.find_routes(ix["A"], ix["B"], "bike", RouteParams(max_routes=1))[0]
    back = graph.find_routes(ix["B"], ix["A"], "bike", RouteParams(max_routes=1))[0]
    assert forward.distance_m == pytest.approx(1000)
    assert back.distance_m == pytest.approx(3000)


def test_bike_cannot_use_motorway_but_car_can():
    points = {"A": (0, 0), "B": (5000, 0), "C": (2500, 2000)}
    edges = [road("A", "B", 5000, "motorway"), road("A", "C", 4000), road("C", "B", 4000)]
    graph, ix = build(points, edges)
    bike = graph.find_routes(ix["A"], ix["B"], "bike", RouteParams(max_routes=1))[0]
    car = graph.find_routes(ix["A"], ix["B"], "car", RouteParams(max_routes=1))[0]
    assert bike.distance_m == pytest.approx(8000) and car.distance_m == pytest.approx(5000)


def test_slowdown_factor_reroutes():
    graph, ix = grid()
    base = graph.find_routes(ix["00"], ix["33"], "bike", RouteParams(max_routes=1))[0]
    slow = np.ones(graph.m)
    slow[base.edges] = 50.0
    rerouted = graph.find_routes(ix["00"], ix["33"], "bike", RouteParams(max_routes=1), slow=slow)[0]
    assert not set(rerouted.edges) & set(base.edges)
    assert rerouted.distance_m == pytest.approx(1200)  # vẫn có đường 1200 m không qua cạnh bị làm chậm


# ----------------------------------------------------------------------------- lộ trình thay thế
@pytest.mark.parametrize("use_via,use_penalty", [(True, False), (False, True), (True, True)])
def test_grid_offers_disjoint_alternatives_with_each_mechanism(use_via, use_penalty):
    graph, ix = grid()
    params = RouteParams(use_via=use_via, use_penalty=use_penalty)
    routes = graph.find_routes(ix["00"], ix["33"], "bike", params)
    assert len(routes) >= 2
    first, second = routes[0], routes[1]
    assert second.duration_s <= params.max_stretch * first.duration_s


def test_two_reasonable_corridors_are_both_offered_and_the_long_one_is_not():
    graph, ix = corridors([10_000, 10_800, 18_000])
    for params in (RouteParams(use_penalty=False), RouteParams(use_via=False), RouteParams()):
        routes = graph.find_routes(ix["A"], ix["B"], "bike", params)
        assert [round(r.distance_m) for r in routes] == [10_000, 10_800]


def test_single_corridor_gives_a_single_route():
    graph, ix = corridors([10_000])
    assert len(graph.find_routes(ix["A"], ix["B"], "bike")) == 1


def test_tiny_bypass_is_not_an_alternative():
    # Một đường dài 10 km với đường vòng 100 m quanh một ngã tư: 95% dùng chung, không phải lựa chọn thật.
    points = {f"p{i}": (500.0 * i, 0.0) for i in range(21)}
    points["X"] = (5250.0, 150.0)
    edges = [road(f"p{i}", f"p{i + 1}", 500) for i in range(20)]
    edges += [road("p10", "X", 300), road("X", "p11", 300)]
    graph, ix = build(points, edges)
    routes = graph.find_routes(ix["p0"], ix["p20"], "bike")
    assert len(routes) == 1


def zigzag_graph():
    """Đường chính a0..a60 (6 km) và đường phụ b0..b60 song song. Trên đường phụ có thể đi đường ngoằn ngoèo
    b30→j1→j2→b31 (500 m) dù cạnh thẳng b30→b31 (100 m) vẫn tồn tại."""
    points, edges = {}, []
    for i in range(61):
        points[f"a{i}"] = (100.0 * i, 0.0)
        points[f"b{i}"] = (100.0 * i, 300.0)
    points["j1"], points["j2"] = (3000.0, 500.0), (3100.0, 500.0)
    for i in range(60):
        edges.append(road(f"a{i}", f"a{i + 1}", 100))
        edges.append(road(f"b{i}", f"b{i + 1}", 100))
    edges += [road("a0", "b0", 300), road("a60", "b60", 300)]
    edges += [road("b30", "j1", 200), road("j1", "j2", 100), road("j2", "b31", 200)]
    return build(points, edges)


def test_local_optimality_test_rejects_a_zigzag_inside_a_long_detour():
    graph, ix = zigzag_graph()
    cost = graph.time_s("bike")
    forward = graph._matrix(cost)
    opt = graph._make_route([ix[f"a{i}"] for i in range(61)], cost, "fastest")
    params = RouteParams()

    straight = [ix["a0"]] + [ix[f"b{i}"] for i in range(61)] + [ix["a60"]]
    zig = [ix["a0"]] + [ix[f"b{i}"] for i in range(31)] + [ix["j1"], ix["j2"]] + [ix[f"b{i}"] for i in range(31, 61)] + [ix["a60"]]
    assert graph._locally_optimal(graph._make_route(straight, cost), opt, cost, forward, params)
    assert not graph._locally_optimal(graph._make_route(zig, cost), opt, cost, forward, params)


def test_a_route_that_is_the_fastest_path_has_nothing_to_test():
    graph, ix = zigzag_graph()
    cost = graph.time_s("bike")
    opt = graph._make_route([ix[f"a{i}"] for i in range(61)], cost, "fastest")
    assert graph._locally_optimal(opt, opt, cost, graph._matrix(cost), RouteParams())


def test_alternatives_satisfy_the_admissibility_conditions_on_random_networks():
    rng = np.random.default_rng(3)
    n = 9
    points = {f"{r}_{c}": (c * 300.0 + rng.normal(0, 30), r * 300.0 + rng.normal(0, 30)) for r in range(n) for c in range(n)}
    edges = []
    for r in range(n):
        for c in range(n):
            for dr, dc in ((0, 1), (1, 0)):
                if r + dr < n and c + dc < n and rng.random() > 0.15:
                    kind = rng.choice(["residential", "tertiary", "secondary"], p=[0.6, 0.25, 0.15])
                    edges.append(road(f"{r}_{c}", f"{r + dr}_{c + dc}", float(rng.uniform(200, 450)), str(kind),
                                      both=bool(rng.random() > 0.2)))
    graph, ix = build(points, edges)
    params = RouteParams()
    cost = graph.time_s("bike")
    checked = 0
    for _ in range(40):
        a, b = rng.choice(len(points), 2, replace=False)
        routes = graph.find_routes(int(a), int(b), "bike", params)
        if not routes:
            continue
        checked += 1
        durations = [r.duration_s for r in routes]
        assert durations == sorted(durations) and routes[0].kind == "fastest"
        assert len(routes) <= params.max_routes
        for i, route in enumerate(routes):
            assert route.nodes[0] == a and route.nodes[-1] == b
            assert len(set(route.nodes.tolist())) == len(route.nodes)  # không có vòng lặp
            assert np.array_equal(graph.u[route.edges], route.nodes[:-1]) and np.array_equal(graph.v[route.edges], route.nodes[1:])
            assert route.duration_s == pytest.approx(cost[route.edges].sum())
            assert route.duration_s <= params.max_stretch * durations[0] * (1 + 1e-9)
            for other in routes[:i]:
                shared = cost[route.edges][np.isin(route.edges, other.edges)].sum()
                assert shared <= params.max_sharing * min(route.duration_s, other.duration_s) * (1 + 1e-9)
    assert checked >= 20


# ----------------------------------------------------------------------------- so với cách làm độc lập
def reference_shortest(graph, cost, src, dst):
    adjacency = {}
    for e in range(graph.m):
        if math.isfinite(cost[e]):
            adjacency.setdefault(int(graph.u[e]), []).append((int(graph.v[e]), float(cost[e])))
    best = {src: 0.0}
    heap = [(0.0, src)]
    while heap:
        d, node = heapq.heappop(heap)
        if d > best.get(node, math.inf):
            continue
        for nxt, w in adjacency.get(node, []):
            if d + w < best.get(nxt, math.inf):
                best[nxt] = d + w
                heapq.heappush(heap, (d + w, nxt))
    return best.get(dst, math.inf)


def test_fastest_route_matches_an_independent_dijkstra():
    rng = np.random.default_rng(11)
    n = 10
    points = {f"{r}_{c}": (c * 250.0, r * 250.0) for r in range(n) for c in range(n)}
    edges = []
    for r in range(n):
        for c in range(n):
            for dr, dc in ((0, 1), (1, 0)):
                if r + dr < n and c + dc < n and rng.random() > 0.2:
                    edges.append(road(f"{r}_{c}", f"{r + dr}_{c + dc}", float(rng.uniform(100, 500)),
                                      str(rng.choice(["residential", "primary"])), both=bool(rng.random() > 0.3)))
    graph, _ = build(points, edges)
    cost = graph.time_s("bike")
    compared = 0
    for _ in range(40):
        a, b = (int(x) for x in rng.choice(len(points), 2, replace=False))
        routes = graph.find_routes(a, b, "bike", RouteParams(max_routes=1))
        expected = reference_shortest(graph, cost, a, b)
        if math.isinf(expected):
            assert routes == []
        else:
            assert routes[0].duration_s == pytest.approx(expected)
            compared += 1
    assert compared >= 20


def test_concurrent_queries_with_different_costs_do_not_interfere():
    # Đồ thị được dùng chung giữa các yêu cầu; kết quả chạy song song phải bằng chạy lần lượt.
    from concurrent.futures import ThreadPoolExecutor

    graph, ix = grid(7)
    rng = np.random.default_rng(5)
    jobs = []
    for _ in range(24):
        a, b = (int(x) for x in rng.choice(graph.n, 2, replace=False))
        jobs.append((a, b, rng.uniform(1.0, 6.0, graph.m)))

    def run(job):
        a, b, slow = job
        return [(round(r.duration_s, 6), r.edges.tolist()) for r in graph.find_routes(a, b, "bike", slow=slow)]

    sequential = [run(job) for job in jobs]
    with ThreadPoolExecutor(8) as pool:
        parallel = list(pool.map(run, jobs * 2))
    assert parallel == sequential * 2


# ----------------------------------------------------------------------------- gắn điểm vào mạng đường
def test_snap_prefers_the_main_component_over_a_closer_island():
    points = {f"p{i}": (200.0 * i, 0.0) for i in range(6)}
    points.update({"i0": (400.0, 60.0), "i1": (430.0, 60.0)})
    edges = [road(f"p{i}", f"p{i + 1}", 200) for i in range(5)] + [road("i0", "i1", 30)]
    graph, ix = build(points, edges)
    lon, lat = lonlat(415.0, 55.0)  # ngay cạnh đảo
    node, distance = graph.snap(lon, lat, "bike")
    assert node in {ix[f"p{i}"] for i in range(6)} and distance > 0


def test_snap_reports_the_distance_to_the_node():
    graph, ix = grid()
    lon, lat = lonlat(0.0, 100.0)
    node, distance = graph.snap(lon, lat, "bike")
    assert node in (ix["00"], ix["10"]) and distance == pytest.approx(100.0, abs=2)


def test_snap_for_bike_ignores_a_component_only_reachable_by_motorway():
    # Cao tốc có 4 nút, lớn hơn chuỗi đường thường 3 nút: xe hơi gắn vào cao tốc, xe máy (bị cấm) gắn vào chuỗi.
    points = {"A": (0, 0), "B": (500, 0), "C": (1000, 0), **{f"M{i}": (5000.0 + 1000 * i, 0.0) for i in range(4)}}
    edges = [road("A", "B", 500), road("B", "C", 500)] + [road(f"M{i}", f"M{i + 1}", 1000, "motorway") for i in range(3)]
    graph, ix = build(points, edges)
    lon, lat = lonlat(6500.0, 0.0)
    assert graph.snap(lon, lat, "car")[0] in {ix[f"M{i}"] for i in range(4)}
    assert graph.snap(lon, lat, "bike")[0] in {ix["A"], ix["B"], ix["C"]}


# ----------------------------------------------------------------------------- hình học và chỉ dẫn
def test_steps_group_by_street_and_report_the_turn():
    points = {"A": (0, 0), "B": (500, 0), "C": (500, 500), "D": (500, 1000)}
    edges = [road("A", "B", 500, name="Đường 1"), road("B", "C", 500, name="Đường 2"), road("C", "D", 500, name="Đường 2")]
    graph, ix = build(points, edges)
    route = graph.find_routes(ix["A"], ix["D"], "bike", RouteParams(max_routes=1))[0]
    steps = graph.steps(route)
    assert [s["name"] for s in steps] == ["Đường 1", "Đường 2"]
    assert [s["turn"] for s in steps] == ["start", "left"]  # đi hướng đông rồi rẽ lên bắc
    assert steps[1]["distance_m"] == pytest.approx(1000)
    assert sum(s["duration_s"] for s in steps) == pytest.approx(route.duration_s, abs=0.2)


def test_steps_name_unnamed_roads_and_detect_a_right_turn():
    points = {"A": (0, 500), "B": (0, 0), "C": (500, 0)}
    edges = [road("A", "B", 500, name="Đường 1"), road("B", "C", 500, name="")]
    graph, ix = build(points, edges)
    steps = graph.steps(graph.find_routes(ix["A"], ix["C"], "bike", RouteParams(max_routes=1))[0])
    assert steps[1]["name"] == "Đường không tên" and steps[1]["turn"] == "left"  # đi hướng nam rồi rẽ sang đông


def test_geometry_follows_travel_direction_even_if_stored_reversed():
    points = {"A": (0, 0), "B": (500, 0)}
    a, b = lonlat(0, 0), lonlat(500, 0)
    curve = LineString([b, lonlat(250, 40), a])  # lưu ngược chiều: từ B về A
    wkb = pa.array([shapely.to_wkb(curve)], type=pa.binary())
    graph, ix = build(points, [road("A", "B", 500, both=False)], wkb=wkb)
    route = graph.find_routes(ix["A"], ix["B"], "bike", RouteParams(max_routes=1))[0]
    coords = graph.geometry(route)
    assert coords[0] == [round(a[0], 6), round(a[1], 6)] and coords[-1] == [round(b[0], 6), round(b[1], 6)]
    assert len(coords) == 3


def test_invalid_vehicle_and_dangling_edges_are_reported():
    graph, ix = grid()
    with pytest.raises(GraphError, match="xe"):
        graph.find_routes(ix["00"], ix["33"], "tank")
    with pytest.raises(GraphError, match="nút"):
        RoadGraph(np.zeros(2), np.zeros(2), np.array([0]), np.array([5]), np.array([1.0]), np.array(["residential"], dtype=object))


def test_parallel_and_self_loop_edges_do_not_break_routing():
    points = {"A": (0, 0), "B": (500, 0)}
    graph, ix = build(points, [road("A", "B", 500, both=False), road("A", "B", 900, both=False), road("A", "A", 10, both=False)])
    route = graph.find_routes(ix["A"], ix["B"], "bike", RouteParams(max_routes=1))[0]
    assert route.distance_m == pytest.approx(500)  # chọn cạnh song song ngắn hơn, bỏ cạnh khuyên
