from __future__ import annotations

from fastapi import FastAPI

from floodrisk.api import routes_places, routes_risk, routes_route, settings
from floodrisk.api.context import Context
from floodrisk.api.goong import Goong


def create_app() -> FastAPI:
    app = FastAPI(
        title="Bản đồ nguy cơ ngập",
        description="Máy chủ của lớp bản đồ nguy cơ ngập đường cho TP.HCM và Đà Nẵng.",
    )
    ctx = Context(goong=Goong(settings.goong_api_key()))
    app.state.ctx = ctx
    routes_risk.register(app, ctx)
    routes_places.register(app, ctx)
    routes_route.register(app, ctx)
    return app
