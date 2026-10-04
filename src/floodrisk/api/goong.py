from __future__ import annotations

import httpx

BASE = "https://rsapi.goong.io/v2"


class GoongError(Exception):
    pass


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

    def reverse(self, lat: float, lon: float) -> dict:
        """Địa chỉ của một tọa độ. Không có kết quả thì trả các trường rỗng, không phải lỗi."""
        results = self._get("/geocode", {"latlng": f"{lat},{lon}"}).get("results") or []
        if not results:
            return {"name": "", "address": "", "place_id": None}
        first = results[0]
        return {"name": first.get("name", ""), "address": first.get("formatted_address", ""),
                "place_id": first.get("place_id")}
