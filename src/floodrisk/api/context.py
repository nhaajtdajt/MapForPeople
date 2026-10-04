from __future__ import annotations

import threading
from dataclasses import dataclass, field

from floodrisk import config
from floodrisk.api.goong import Goong
from floodrisk.api.graphroute import RoadGraph


@dataclass
class Context:
    goong: Goong
    last_refresh: str | None = None
    last_error: str | None = None
    traffic: dict = field(default_factory=dict)
    graphs: dict = field(default_factory=dict)
    _graph_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

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
