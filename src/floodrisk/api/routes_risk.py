from __future__ import annotations

import json

from fastapi import FastAPI

from floodrisk import config
from floodrisk.api import ports, settings
from floodrisk.api.context import Context


def data_kind() -> str:
    """`sample` khi thư mục dữ liệu là dữ liệu mẫu (có file đánh dấu), ngược lại `real`."""
    return "sample" if (config.data_dir() / "processed" / "SAMPLE").exists() else "real"


def validated_cities() -> set[str]:
    try:
        choice = json.loads(config.model_choice_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return set(choice.get("validated") or [])


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
