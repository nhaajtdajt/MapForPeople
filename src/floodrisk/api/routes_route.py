from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException

from floodrisk import config
from floodrisk.api.context import Context
from floodrisk.api.graphroute import VEHICLES, GraphError, Route, RouteParams

VN = timezone(timedelta(hours=7))
LONG_DETOUR = 1.5  # lộ trình lâu hơn đường nhanh nhất quá 1,5 lần thì cắm cờ cho giao diện
ESTIMATE_NOTE = "Thời gian là ước lượng theo loại đường, chưa tính giao thông."


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
    def route_json(index: int, route: Route, fastest: Route, graph, now: datetime) -> dict:
        return {
            "id": index,
            "kind": route.kind,
            "engine": "own",
            "estimated": True,
            "recommended": index == 0,
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
        notes = [ESTIMATE_NOTE]
        for label, key in (("Điểm đi", "origin"), ("Điểm đến", "destination")):
            if snapped[key]["distance_m"] > 50:
                notes.append(f"{label} được gắn vào đường gần nhất, cách {snapped[key]['distance_m']:.0f} m.")
        return {
            "routes": [route_json(i, r, routes[0], graph, now) for i, r in enumerate(routes)],
            "snapped": {k: {f: v for f, v in s.items() if f != "node"} for k, s in snapped.items()},
            "traffic": {"source": "none", "observed_at": None},
            "advice": None,
            "notes": notes,
        }
