from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from floodrisk.api import routes_live, routes_places, routes_risk, routes_route, settings
from floodrisk.api.context import Context
from floodrisk.api.goong import Goong
from floodrisk.live import hydro


class WebApp(StaticFiles):
    """Giao diện đã dựng. Trang (index.html) không được giữ lại trong trình duyệt: trước đây trình duyệt dùng lại trang cũ sau
    mỗi lần triển khai, nên vẫn chạy mã cũ. Các file trong assets/ có tên đổi theo nội dung nên giữ lâu được."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if path.replace("\\", "/").startswith("assets/"):  # trên Windows đường dẫn dùng dấu \
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="Bản đồ nguy cơ ngập",
        description="Máy chủ của lớp bản đồ nguy cơ ngập đường cho TP.HCM và Đà Nẵng.",
    )
    ctx = Context(goong=Goong(settings.goong_api_key()))
    if settings.refresh_minutes() > 0:  # 0 là chế độ không gọi mạng (kiểm thử, dữ liệu mẫu)
        ctx.hydro_sources["hcm"] = hydro
    app.state.ctx = ctx
    routes_risk.register(app, ctx)
    routes_places.register(app, ctx)
    routes_route.register(app, ctx)
    routes_live.register(app, ctx)
    # Bản triển khai chạy một dịch vụ duy nhất: máy chủ phục vụ luôn giao diện đã dựng (spec 07, mục 1.1).
    # Gắn sau cùng để mọi đường dẫn /api/... vẫn do các hàm ở trên trả lời.
    dist = settings.web_dist()
    if (dist / "index.html").exists():
        app.mount("/", WebApp(directory=dist, html=True), name="web")
    return app
