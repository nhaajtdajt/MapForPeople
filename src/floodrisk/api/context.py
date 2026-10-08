from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from floodrisk import config
from floodrisk.api import ports, settings
from floodrisk.api.goong import Goong
from floodrisk.api.graphroute import RoadGraph

RISK_RETRY_S = 120  # sau một lần tính hỏng, chờ chừng này rồi mới thử lại


@dataclass
class Context:
    goong: Goong
    last_refresh: str | None = None
    last_error: str | None = None
    traffic: dict = field(default_factory=dict)
    graphs: dict = field(default_factory=dict)
    rain_fetch: Callable | None = None  # nguồn mưa cho mô hình; để trống thì gọi Open-Meteo. Kiểm thử thay bằng hàm cố định.
    models: dict = field(default_factory=dict)
    snapshots: dict = field(default_factory=dict)  # thành phố -> (Snapshot, lúc tính theo time.monotonic)
    risk_failures: dict = field(default_factory=dict)  # thành phố -> (lời báo lỗi, lúc hỏng)
    _graph_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _risk_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def traffic_status(self) -> dict:
        """Nguồn giao thông của từng thành phố. Mặc định là bảng điển hình cho tới khi có TomTom (spec 09)."""
        return {key: self.traffic.get(key, {"source": "typical", "observed_at": None}) for key in config.CITIES}

    def graph(self, city: str) -> RoadGraph:
        """Mạng đường của thành phố, nạp ở lần gọi đầu rồi giữ trong bộ nhớ.

        Lỗi nạp (thiếu file) không được ghi nhớ, nên chép file vào là dùng được ngay, không cần khởi động lại máy chủ.
        Muốn nạp lại file đã đổi thì khởi động lại máy chủ.
        """
        with self._graph_lock:
            if city not in self.graphs:
                self.graphs[city] = RoadGraph.load(city)
            return self.graphs[city]

    def model(self, city: str):
        """Các file mô hình của thành phố, nạp ở lần gọi đầu. Thiếu file thì ném FileNotFoundError và không ghi nhớ."""
        if city not in self.models:
            self.models[city] = ports.CityModel(city)
        return self.models[city]

    def risk(self, city: str):
        """Mức nguy cơ lúc này: (bản tính gần nhất hoặc None, lời báo lỗi hoặc None).

        Tính lại khi đã sang giờ mới hoặc bản đang giữ cũ hơn REFRESH_MINUTES. Tính hỏng (mất mạng, nguồn mưa lỗi)
        thì giữ bản cũ, trả kèm lời báo, và thử lại sau RISK_RETRY_S giây.
        """
        with self._risk_lock:
            model = self.model(city)
            held = self.snapshots.get(city)
            failure = self.risk_failures.get(city)
            now = time.monotonic()
            max_age_s = max(settings.refresh_minutes(), 10) * 60
            fresh = held is not None and now - held[1] < max_age_s and held[0].hours[0].valid_time == ports.current_hour()
            if fresh or (failure is not None and now - failure[1] < RISK_RETRY_S):
                return (held[0] if held else None), (None if fresh else failure[0])
            try:
                snapshot = model.snapshot(fetch=self.rain_fetch) if self.rain_fetch else model.snapshot()
            except Exception as exc:  # mọi lỗi của nguồn mưa: giữ bản cũ thay vì làm hỏng cả bản đồ
                message = f"Chưa cập nhật được mức nguy cơ: {type(exc).__name__}: {exc}"
                self.risk_failures[city] = (message, now)
                self.last_error = message
                return (held[0] if held else None), message
            self.snapshots[city] = (snapshot, now)
            self.risk_failures.pop(city, None)
            self.last_refresh = snapshot.generated_at.isoformat(timespec="seconds")
            return snapshot, None
