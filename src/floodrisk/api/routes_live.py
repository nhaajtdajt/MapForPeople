"""Camera giao thông và báo ngập (ghi chú 11, QĐ4): xem ảnh đường lúc này, Gemini đọc ảnh, người dùng báo ngập một chạm."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from floodrisk import config
from floodrisk.api import settings
from floodrisk.api.context import Context
from floodrisk.api.graphroute import GraphError
from floodrisk.live import cameras, reports

CAMERA_CITY = "hcm"  # cổng camera chỉ có TP.HCM
CAMERA_CONFIDENCE = 0.75  # Gemini phải chắc từng này thì lượt đọc mới thành báo cáo
DEPTH_LABEL = {"light": "dưới 10 cm", "medium": "10 tới 30 cm", "high": "trên 30 cm"}


class ReportIn(BaseModel):
    city: str = "hcm"
    lat: float
    lon: float
    status: str  # "flooded" | "clear"
    depth: str | None = None  # "light" | "medium" | "high"
    user: str  # mã do máy của người dùng tự sinh, để một người chỉ tính một lần cho mỗi tuyến trong 30 phút


def register(app: FastAPI, ctx: Context) -> None:
    def route_or_422(city: str, lat: float, lon: float):
        if city not in config.CITIES:
            raise HTTPException(404, f"Không có thành phố '{city}'")
        try:
            found = ctx.route_at(city, lat, lon)
        except (FileNotFoundError, GraphError):
            raise HTTPException(404, "Thành phố này chưa nhận báo ngập") from None
        if found is None:
            raise HTTPException(422, "Điểm này không nằm gần con đường nào")
        return found

    @app.get("/api/cameras")
    def camera_list(city: str = "hcm"):
        if city != CAMERA_CITY or CAMERA_CITY not in ctx.hydro_sources:
            return []
        return [{"id": c["id"], "name": c["name"], "lat": c["lat"], "lon": c["lon"], "has_image": c["status"] != "NOT_IMAGE"}
                for c in cameras.registry()]

    @app.get("/api/cameras/{cam_id}.jpg")
    def camera_image(cam_id: str):
        image = cameras.snapshot(cam_id) if cam_id.isalnum() else None
        if image is None:
            raise HTTPException(404, "Camera này hiện không có hình")
        return Response(image, media_type="image/jpeg", headers={"Cache-Control": "max-age=10"})

    @app.post("/api/cameras/{cam_id}/read")
    def camera_read(cam_id: str):
        """Gemini đọc camera này (mất khoảng nửa phút). Đọc thấy ngập hoặc khô đủ chắc thì thành một báo cáo trên tuyến có camera."""
        cam = next((c for c in cameras.registry() if c["id"] == cam_id), None)
        if cam is None:
            raise HTTPException(404, "Không có camera này")
        try:
            reading = cameras.read(cam)
        except (cameras.NoKey, cameras.OutOfQuota) as exc:
            raise HTTPException(503, str(exc)) from None
        report = None
        sure = reading.get("state") == "ok" and reading.get("confidence", 0) >= CAMERA_CONFIDENCE
        if sure and not reading.get("reported"):
            found = ctx.route_at(CAMERA_CITY, cam["lat"], cam["lon"])
            if found is not None:
                row, route_id, _ = found
                status = "flooded" if reading["flooded"] else "clear"
                report = reports.add(settings.db_path(), CAMERA_CITY, row, route_id, cam["lat"], cam["lon"], status, reading.get("depth"),
                                     f"camera:{cam_id}", source="camera", note=reading.get("evidence"))
                reading["reported"] = True  # kết quả được giữ vài phút: không ghi hai báo cáo cho cùng một lượt đọc
        return {"camera": {"id": cam["id"], "name": cam["name"]}, "reading": reading, "report": report}

    @app.post("/api/reports")
    def report_add(body: ReportIn):
        row, route_id, name = route_or_422(body.city, body.lat, body.lon)
        try:
            report = reports.add(settings.db_path(), body.city, row, route_id, body.lat, body.lon, body.status, body.depth, body.user[:64])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        return {"report": report, "route": {"id": row, "name": name or "Đường chưa có tên"}}

    @app.get("/api/reports")
    def report_list(city: str = "hcm"):
        """Các báo cáo còn hiệu lực, mới nhất trước, để vẽ lên bản đồ."""
        if city not in config.CITIES:
            raise HTTPException(404, f"Không có thành phố '{city}'")
        return [{"id": r["id"], "route": r["route_row"], "lat": r["lat"], "lon": r["lon"], "status": r["status"], "depth": r["depth"],
                 "depth_label": DEPTH_LABEL.get(r["depth"]), "source": r["source"], "note": r["note"], "at": r["at"]}
                for r in reports.active(settings.db_path(), city)]
