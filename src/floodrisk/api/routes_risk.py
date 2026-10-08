from __future__ import annotations

import csv
import hashlib
import json

from fastapi import FastAPI, HTTPException, Request, Response

from floodrisk import config
from floodrisk.api import ports, settings
from floodrisk.api.context import Context

LAYER_CACHE = "public, max-age=3600"


def data_kind() -> str:
    """`sample` khi thư mục dữ liệu là dữ liệu mẫu (có file đánh dấu), ngược lại `real`."""
    return "sample" if (config.data_dir() / "processed" / "SAMPLE").exists() else "real"


def validated_cities() -> set[str]:
    try:
        choice = json.loads(config.model_choice_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return set(choice.get("validated") or [])


def _city(city: str) -> str:
    if city not in config.CITIES:
        raise HTTPException(404, f"Không có thành phố '{city}'")
    return city


def _cause(cause) -> dict:
    return {"state": ports.STATE_NAMES[cause.state], "trigger": round(cause.trigger, 6), **cause.inputs}


def _file_version(path) -> str:
    stat = path.stat()
    return hashlib.sha1(f"{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()[:10]


def flood_points(city: str) -> dict:
    """Các điểm ngập cơ quan chức năng đã công bố, đã định vị được trên mạng đường (ghi chú 12, mục 3)."""
    path = config.flood_points_path(city)
    features = []
    if path.exists():
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("lon") or not row.get("lat"):
                    continue
                features.append({
                    "type": "Feature", "id": int(row["no"]),
                    "geometry": {"type": "Point", "coordinates": [float(row["lon"]), float(row["lat"])]},
                    "properties": {"no": int(row["no"]), "cause": row["cause"], "place": row["place"],
                                   "located_by": row["located_by"], "routes": row.get("route_ids", "")},
                })
    return {"type": "FeatureCollection", "features": features,
            "source": "Phòng CSGT Công an TP.HCM (PC08), công bố ngày 06/10/2026"}


def register(app: FastAPI, ctx: Context) -> None:
    @app.get("/api/health")
    def health():
        return {
            "ok": True,
            "test_tools": settings.test_tools_enabled(),
            "data": data_kind(),
            "parts": ports.status(),
            "traffic": ctx.traffic_status(),
            "last_refresh": ctx.last_refresh,
            "last_error": ctx.last_error,
        }

    @app.get("/api/cities")
    def cities():
        validated = validated_cities()
        return [
            {"key": c.key, "name": c.name, "center": list(c.center), "bbox": list(c.bbox),
             "has_tide": c.has_tide, "validated": c.key in validated}
            for c in config.CITIES.values()
        ]

    @app.get("/api/risk")
    def risk(city: str = "hcm"):
        """Mức nguy cơ lúc này và hai giờ tới: trạng thái mưa và triều của cả thành phố theo Mô hình 2.

        Mức của từng tuyến suy ra từ trạng thái này và nhóm của tuyến trong lớp `/api/risk/routes`
        (`br`, `bt`: 2 là nhóm A, 1 là nhóm B): báo động thì nhóm A lên mức cao và nhóm B lên mức vừa;
        cảnh giác thì chỉ nhóm A lên mức vừa; lấy mức lớn hơn giữa mưa và triều.
        """
        _city(city)
        try:
            snapshot, error = ctx.risk(city)
            model = ctx.model(city)
        except FileNotFoundError:
            raise HTTPException(404, "Chưa có mô hình cho thành phố này trong thư mục dữ liệu đang dùng") from None
        if snapshot is None:
            raise HTTPException(503, error or "Chưa tính được mức nguy cơ")
        layer = config.risk_layer_path(city)
        return {
            "city": city,
            "model_version": snapshot.model_version,
            "generated_at": snapshot.generated_at.isoformat(timespec="seconds"),
            "rain_source": snapshot.rain_source,
            "stale": error is not None,
            "error": error,
            "hours": [{"valid_time": hour.valid_time.isoformat(), "rain": _cause(hour.rain), "tide": _cause(hour.tide),
                       "counts": model.counts(hour)} for hour in snapshot.hours],
            "layer": {"url": f"/api/risk/routes?city={city}&v={_file_version(layer)}"} if layer.exists() else None,
        }

    @app.get("/api/risk/routes")
    def risk_routes(request: Request, city: str = "hcm"):
        """Hình học các tuyến thuộc nhóm A hoặc B của mô hình (GeoJSON nén gzip). Đổi khi mô hình được dựng lại."""
        path = config.risk_layer_path(_city(city))
        if not path.exists():
            raise HTTPException(404, "Chưa có lớp tuyến cho thành phố này")
        etag = f'"{_file_version(path)}"'
        headers = {"ETag": etag, "Cache-Control": LAYER_CACHE}
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(path.read_bytes(), media_type="application/geo+json", headers={**headers, "Content-Encoding": "gzip"})

    @app.get("/api/risk/points")
    def risk_points(city: str = "hcm"):
        return flood_points(_city(city))
