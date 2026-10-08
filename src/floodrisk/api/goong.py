from __future__ import annotations

import re

import httpx

BASE = "https://rsapi.goong.io/v2"


class GoongError(Exception):
    pass


def decode_polyline(encoded: str, precision: int = 5) -> list[tuple[float, float]]:
    """Giải mã chuỗi polyline của Google/Goong thành danh sách (kinh độ, vĩ độ)."""
    points: list[tuple[float, float]] = []
    index = lat = lon = 0
    while index < len(encoded):
        for axis in (0, 1):
            shift = result = 0
            while True:
                chunk = ord(encoded[index]) - 63
                index += 1
                result |= (chunk & 0x1F) << shift
                shift += 5
                if chunk < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if axis == 0:
                lat += delta
            else:
                lon += delta
        points.append((lon / 10**precision, lat / 10**precision))
    return points


class Goong:
    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=15)

    def _get(self, path: str, params: dict) -> dict:
        if not self.api_key:
            raise GoongError("chưa cấu hình khóa GOONG_API_KEY")
        try:
            res = self.client.get(f"{BASE}{path}", params={**params, "api_key": self.api_key})
        except httpx.HTTPError as exc:
            raise GoongError(f"không kết nối được ({type(exc).__name__})") from exc
        if res.status_code != 200:
            raise GoongError(f"HTTP {res.status_code}")
        return res.json()

    def autocomplete(self, q: str, lat: float | None = None, lon: float | None = None, limit: int = 6) -> list[dict]:
        params: dict = {"input": q, "limit": limit}
        if lat is not None and lon is not None:
            params["location"] = f"{lat},{lon}"
        out = []
        for p in self._get("/place/autocomplete", params).get("predictions") or []:
            fmt = p.get("structured_formatting") or {}
            out.append({
                "place_id": p["place_id"],
                "main": fmt.get("main_text") or p.get("description", ""),
                "secondary": fmt.get("secondary_text", ""),
            })
        return out

    def place(self, place_id: str) -> dict:
        result = self._get("/place/detail", {"place_id": place_id}).get("result") or {}
        location = (result.get("geometry") or {}).get("location")
        if not location:
            raise GoongError("không có tọa độ cho địa điểm này")
        return {"name": result.get("name", ""), "address": result.get("formatted_address", ""),
                "lat": location["lat"], "lon": location["lng"]}

    def directions(self, origin: tuple[float, float], destination: tuple[float, float], vehicle: str = "bike",
                   alternatives: bool = True) -> list[dict]:
        """Lộ trình của Goong. `origin` và `destination` là (vĩ độ, kinh độ). Goong chỉ trả 1 hoặc 2 lộ trình."""
        data = self._get("/direction", {
            "origin": f"{origin[0]},{origin[1]}", "destination": f"{destination[0]},{destination[1]}",
            "vehicle": vehicle, "alternatives": "true" if alternatives else "false",
        })
        routes = []
        for route in data.get("routes") or []:
            legs = route.get("legs") or []
            polyline = route["overview_polyline"]
            routes.append({
                "distance_m": sum(leg["distance"]["value"] for leg in legs),
                "duration_s": sum(leg["duration"]["value"] for leg in legs),
                "polyline": polyline["points"] if isinstance(polyline, dict) else polyline,
                # Chỉ dẫn từng bước của Goong, đã là câu tiếng Việt hoàn chỉnh ("Rẽ phải vào Lê Lai").
                "steps": [{"name": re.sub(r"<[^>]+>", "", step.get("html_instructions") or "").strip(),
                           "distance_m": float(step["distance"]["value"]), "duration_s": float(step["duration"]["value"]), "turn": "text"}
                          for leg in legs for step in leg.get("steps") or []],
            })
        return routes

    def reverse(self, lat: float, lon: float) -> dict:
        """Địa chỉ của một tọa độ. Không có kết quả thì trả các trường rỗng, không phải lỗi."""
        results = self._get("/geocode", {"latlng": f"{lat},{lon}"}).get("results") or []
        if not results:
            return {"name": "", "address": "", "place_id": None}
        first = results[0]
        return {"name": first.get("name", ""), "address": first.get("formatted_address", ""),
                "place_id": first.get("place_id")}
