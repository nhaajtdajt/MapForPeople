from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException

import numpy as np
from scipy.spatial import cKDTree

from floodrisk import config
from floodrisk.api import floodcost, settings
from floodrisk.api.context import Context
from floodrisk.api.goong import GoongError, decode_polyline
from floodrisk.api.graphroute import VEHICLES, GraphError, Route, RouteParams

VN = timezone(timedelta(hours=7))
LONG_DETOUR = 1.5  # lộ trình lâu hơn đường nhanh nhất quá 1,5 lần thì cắm cờ cho giao diện
ESTIMATE_NOTE = "Thời gian là ước lượng theo loại đường, chưa tính giao thông."
FLOOD_NOTE = "Lộ trình đề xuất đã tính mức nguy cơ ngập lúc này; mỗi lộ trình ghi số mét đi qua đường đang có mức."
GOONG_NOTE = "Lộ trình chính do Goong tính. Đường tránh ngập do hệ thống tự tính trên OpenStreetMap: hãy theo biển báo thực tế."
MATCH_STEP_M = 8.0  # dò lộ trình của Goong trên mạng đường: lấy điểm cách nhau chừng này
MATCH_SNAP_M = 12.0  # và gắn vào nút cách không quá chừng này
_node_trees: dict = {}


def edges_along(graph, city: str, coords: list) -> np.ndarray:
    """Các cạnh của mạng đường mà một đường vẽ (kinh độ, vĩ độ) đi qua, để tính lộ trình của Goong qua bao nhiêu đường có mức.

    Gần đúng: trên đường đôi có thể gắn nhầm sang chiều bên kia, nhưng hai chiều cùng tên và cùng mức.
    """
    if len(coords) < 2:
        return np.zeros(0, np.int64)
    if city not in _node_trees:
        _node_trees[city] = cKDTree(graph.project(graph.node_lon, graph.node_lat))
    pts = graph.project(np.array([c[0] for c in coords]), np.array([c[1] for c in coords]))
    dense = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        k = max(1, int(np.hypot(*(b - a)) // MATCH_STEP_M))
        dense += [a + (b - a) * (i / k) for i in range(1, k + 1)]
    dist, idx = _node_trees[city].query(np.array(dense))
    nodes = [int(i) for i, m in zip(idx, dist) if m <= MATCH_SNAP_M]
    edges = []
    for a, b in zip(nodes[:-1], nodes[1:]):
        if a == b:
            continue
        for key in (a * graph.n + b, b * graph.n + a):
            at = int(np.searchsorted(graph._key_sorted, key))
            if at < len(graph._key_sorted) and graph._key_sorted[at] == key:
                edges.append(int(graph._key_order[at]))
                break
    return np.array(sorted(set(edges)), np.int64)


def parse_point(text: str, label: str) -> tuple[float, float]:
    """'vĩ độ,kinh độ' → (vĩ độ, kinh độ)."""
    try:
        lat_text, lon_text = text.split(",")
        lat, lon = float(lat_text), float(lon_text)
    except ValueError:
        raise HTTPException(422, f"{label} phải có dạng vĩ độ,kinh độ (ví dụ 10.7725,106.698)")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(422, f"{label} có tọa độ không hợp lệ")
    return lat, lon


def register(app: FastAPI, ctx: Context) -> None:
    def route_json(index: int, route: Route, fastest: Route, graph, now: datetime, recommended: int, flood) -> dict:
        return {
            "id": index,
            "kind": route.kind,
            "engine": "own",
            "estimated": True,
            "recommended": index == recommended,
            "flood": floodcost.exposure(route.edges, graph.length_m, flood) if flood is not None else None,
            "long_detour": route.duration_s > LONG_DETOUR * fastest.duration_s,
            "distance_m": round(route.distance_m, 1),
            "duration_s": round(route.duration_s),
            "duration_normal_s": round(route.duration_s),
            "arrive_at": (now + timedelta(seconds=route.duration_s)).isoformat(timespec="seconds"),
            "steps": graph.steps(route),
            "geometry": {"type": "LineString", "coordinates": graph.geometry(route)},
        }

    @app.get("/api/route")
    def find_route(city: str, origin: str, destination: str, vehicle: str = "bike"):
        if city not in config.CITIES:
            raise HTTPException(404, f"Thành phố không có trong hệ thống: {city}")
        if vehicle not in VEHICLES:
            raise HTTPException(422, "Loại xe phải là bike (xe máy) hoặc car (ô tô)")
        o_lat, o_lon = parse_point(origin, "Điểm đi")
        d_lat, d_lon = parse_point(destination, "Điểm đến")
        west, south, east, north = config.CITIES[city].bbox
        for label, lat, lon in (("Điểm đi", o_lat, o_lon), ("Điểm đến", d_lat, d_lon)):
            if not (south <= lat <= north and west <= lon <= east):
                raise HTTPException(422, f"{label} nằm ngoài khu vực hỗ trợ của {config.CITIES[city].name}")

        try:
            graph = ctx.graph(city)
        except GraphError as exc:
            raise HTTPException(404, str(exc))

        params = RouteParams()
        snapped = {}
        for label, key, lat, lon in (("Điểm đi", "origin", o_lat, o_lon), ("Điểm đến", "destination", d_lat, d_lon)):
            node, distance = graph.snap(lon, lat, vehicle)
            if distance > params.max_snap_m:
                raise HTTPException(422, f"{label} không gần đường nào (cách đường gần nhất {distance:.0f} m)")
            snapped[key] = {"node": node, "lat": float(graph.node_lat[node]), "lon": float(graph.node_lon[node]),
                            "distance_m": round(distance, 1)}
        if snapped["origin"]["node"] == snapped["destination"]["node"]:
            raise HTTPException(422, "Điểm đi và điểm đến quá gần nhau")

        routes = graph.find_routes(snapped["origin"]["node"], snapped["destination"]["node"], vehicle, params)
        if not routes:
            raise HTTPException(404, "Không tìm được đường giữa hai điểm này")

        now = datetime.now(VN)
        flood = ctx.flood_view(city)
        notes = [ESTIMATE_NOTE] + ([FLOOD_NOTE] if flood is not None else [])
        for label, key in (("Điểm đi", "origin"), ("Điểm đến", "destination")):
            if snapped[key]["distance_m"] > 50:
                notes.append(f"{label} được gắn vào đường gần nhất, cách {snapped[key]['distance_m']:.0f} m.")

        # Đường tránh ngập của hệ thống (ghi chú 11, QĐ5): đường tốt nhất khi các cạnh đang có mức bị làm chậm.
        avoid = None
        slow = base = None
        if flood is not None:
            slow = floodcost.slow_factors(flood)
            base = graph.time_s(vehicle)
            dry = graph.find_routes(snapped["origin"]["node"], snapped["destination"]["node"], vehicle,
                                    RouteParams(max_routes=1, use_via=False, use_penalty=False), slow=slow)
            if dry:
                avoid = dry[0]
                avoid.edge_time = base[avoid.edges]
                avoid.duration_s = float(avoid.edge_time.sum())

        # Lộ trình chính lấy từ Goong khi gọi được (chiều đường và cấm rẽ của Goong đầy đủ hơn OpenStreetMap).
        goong_routes = []
        if settings.refresh_minutes() > 0:  # 0 là chế độ không gọi mạng
            try:
                goong_routes = ctx.goong.directions((o_lat, o_lon), (d_lat, d_lon), vehicle=vehicle)
            except GoongError:
                goong_routes = []  # Goong lỗi hoặc hết hạn mức: dùng bộ tìm đường của hệ thống
        if goong_routes:
            fastest_s = min(g["duration_s"] for g in goong_routes)
            items = []
            for g in sorted(goong_routes, key=lambda g: g["duration_s"]):
                coords = decode_polyline(g["polyline"])
                seen = floodcost.exposure(edges_along(graph, city, coords), graph.length_m, flood) if flood is not None else None
                items.append({"kind": "fastest" if not items else "alternative", "engine": "goong", "estimated": False,
                              "distance_m": round(float(g["distance_m"]), 1), "duration_s": round(g["duration_s"]), "flood": seen, "steps": g.get("steps", []),
                              "geometry": {"type": "LineString", "coordinates": [[c[0], c[1]] for c in coords]}})
            if avoid is not None:
                seen = floodcost.exposure(avoid.edges, graph.length_m, flood)
                worst = lambda f: f["confirmed_m"] + f["history_m"]  # noqa: E731
                if worst(seen) < min(worst(i["flood"]) for i in items):  # chỉ thêm khi nó thật sự né được đường ngập
                    items.append({"kind": "flood_avoid", "engine": "own", "estimated": True, "distance_m": round(avoid.distance_m, 1),
                                  "duration_s": round(avoid.duration_s), "flood": seen, "steps": graph.steps(avoid),
                                  "geometry": {"type": "LineString", "coordinates": graph.geometry(avoid)}})
                    notes.append(GOONG_NOTE)
            for item in items:
                item["long_detour"] = item["duration_s"] > LONG_DETOUR * fastest_s
            if flood is not None:
                ok = [i for i in items if not i["long_detour"]] or items
                best = min(ok, key=lambda i: (i["flood"]["confirmed_m"], i["flood"]["history_m"], i["duration_s"]))
            else:
                best = items[0]
            for index, item in enumerate(items):
                item.update(id=index, recommended=item is best, duration_normal_s=item["duration_s"],
                            arrive_at=(now + timedelta(seconds=item["duration_s"])).isoformat(timespec="seconds"))
            return {"routes": items, "snapped": {k: {f: v for f, v in s_.items() if f != "node"} for k, s_ in snapped.items()},
                    "traffic": {"source": "goong", "observed_at": None}, "advice": None,
                    "notes": [n for n in notes if n != ESTIMATE_NOTE]}

        # Không có Goong: toàn bộ lộ trình do hệ thống tự tính.
        recommended = 0
        if flood is not None:
            if avoid is not None and not any(np.array_equal(avoid.edges, r.edges) for r in routes):
                routes.append(avoid)
                routes.sort(key=lambda r: r.duration_s)
                for r in routes[1:]:
                    r.kind = "flood_avoid" if r is avoid else "alternative"
            recommended = int(np.argmin([float((base[r.edges] * slow[r.edges]).sum()) for r in routes]))
        return {
            "routes": [route_json(i, r, routes[0], graph, now, recommended, flood) for i, r in enumerate(routes)],
            "snapped": {k: {f: v for f, v in s.items() if f != "node"} for k, s in snapped.items()},
            "traffic": {"source": "none", "observed_at": None},
            "advice": None,
            "notes": notes,
        }
