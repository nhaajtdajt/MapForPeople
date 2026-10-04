from __future__ import annotations

from fastapi import FastAPI, HTTPException

from floodrisk.api.context import Context
from floodrisk.api.goong import GoongError

# Khung thô của lãnh thổ Việt Nam; chỉ để chặn tọa độ rõ ràng sai trước khi gọi Goong.
VIETNAM_BBOX = (102.0, 8.0, 110.0, 23.6)  # tây, nam, đông, bắc
FAIL = "Không tìm được địa điểm lúc này"


def register(app: FastAPI, ctx: Context) -> None:
    def goong_failed(exc: GoongError) -> HTTPException:
        return HTTPException(502, f"{FAIL} (Goong lỗi: {exc})")

    @app.get("/api/places/autocomplete")
    def autocomplete(q: str, lat: float | None = None, lon: float | None = None):
        if not q.strip():
            return []
        try:
            return ctx.goong.autocomplete(q.strip(), lat, lon)
        except GoongError as exc:
            raise goong_failed(exc)

    @app.get("/api/places/detail")
    def detail(place_id: str):
        try:
            return ctx.goong.place(place_id)
        except GoongError as exc:
            raise goong_failed(exc)

    @app.get("/api/places/reverse")
    def reverse(lat: float, lon: float):
        west, south, east, north = VIETNAM_BBOX
        if not (south <= lat <= north and west <= lon <= east):
            raise HTTPException(422, "Điểm này nằm ngoài lãnh thổ Việt Nam")
        try:
            return ctx.goong.reverse(lat, lon)
        except GoongError as exc:
            raise goong_failed(exc)
