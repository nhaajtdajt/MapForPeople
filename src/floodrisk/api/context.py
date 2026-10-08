from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from floodrisk import config
from floodrisk.api import floodcost, ports, settings
from floodrisk.live import local as live_local
from floodrisk.live import reports as live_reports
from floodrisk.api.goong import Goong
from floodrisk.api.graphroute import RoadGraph

RISK_RETRY_S = 120  # sau một lần tính hỏng, chờ chừng này rồi mới thử lại
LOCAL_TTL_S = 600  # trạm mưa báo từng giờ, cổng số liệu chậm: đọc lại mỗi 10 phút là đủ


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
    hydro_sources: dict = field(default_factory=dict)  # thành phố -> nguồn trạm mưa và triều; trống thì chỉ dùng mô hình
    locals: dict = field(default_factory=dict)  # thành phố -> (Local, lúc đọc, bản tính của mô hình đã dùng)
    edge_routes: dict = field(default_factory=dict)  # thành phố -> cạnh gắn vào tuyến nào
    _local_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
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
            if held is None:
                # Vừa khởi động: lấy bản tính gần nhất đã lưu, để nguồn mưa có lỗi thì bản đồ vẫn có mức (ghi là số liệu cũ).
                saved = self._saved_risk(city)
                if saved is not None:
                    held = self.snapshots[city] = (saved, float("-inf"))
            failure = self.risk_failures.get(city)
            now = time.monotonic()
            max_age_s = max(settings.refresh_minutes(), 10) * 60
            fresh = held is not None and now - held[1] < max_age_s and held[0].hours[0].valid_time == ports.current_hour()
            if fresh or (failure is not None and now - failure[1] < RISK_RETRY_S and held is not None):
                return held[0], (None if fresh else failure[0])
            try:
                snapshot = model.snapshot(fetch=self.rain_fetch) if self.rain_fetch else model.snapshot()
            except Exception as exc:  # mọi lỗi của nguồn mưa: giữ bản cũ thay vì làm hỏng cả bản đồ
                message = f"Chưa cập nhật được mức nguy cơ: {type(exc).__name__}: {exc}"
                self.risk_failures[city] = (message, now)
                self.last_error = message
                if held is None or held[0].hours[0].rain.inputs.get("missing"):
                    # Chưa có bản tính đủ nào: dựng bản thiếu mưa (triều vẫn đủ), để trạm mưa, Phú An và báo cáo vẫn nâng được mức.
                    try:
                        held = self.snapshots[city] = (model.snapshot_without_rain(), float("-inf"))
                    except Exception:
                        return None, message
                return held[0], message
            self.snapshots[city] = (snapshot, now)
            self._save_risk(city, snapshot)
            self.risk_failures.pop(city, None)
            self.last_refresh = snapshot.generated_at.isoformat(timespec="seconds")
            return snapshot, None

    def accept_snapshot(self, city: str, record: dict) -> None:
        """Nhận một bản tính của mô hình do máy khác tính (khi máy chủ này không gọi được nguồn mưa)."""
        snapshot = ports.from_record(record)
        if snapshot.city != city:
            raise ValueError("Bản tính không phải của thành phố này")
        self.model(city)  # thành phố chưa có mô hình thì báo thiếu file
        with self._risk_lock:
            self.snapshots[city] = (snapshot, time.monotonic())
            self._save_risk(city, snapshot)
            self.risk_failures.pop(city, None)
            self.last_refresh = snapshot.generated_at.isoformat(timespec="seconds")

    @staticmethod
    def _risk_file(city: str):
        return config.live_dir() / f"last_risk_{city}.json"

    def _save_risk(self, city: str, snapshot) -> None:
        try:
            path = self._risk_file(city)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(ports.to_record(snapshot), ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass  # không lưu được thì lần khởi động sau tính lại từ đầu

    def _saved_risk(self, city: str):
        try:
            return ports.from_record(json.loads(self._risk_file(city).read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError):
            return None

    def local(self, city: str, snapshot):
        """Số đo tại chỗ (trạm mưa, mực nước Phú An) đã áp lên giờ đầu của `snapshot`, hoặc None nếu thành phố không có nguồn."""
        source = self.hydro_sources.get(city)
        if source is None or snapshot is None:
            return None
        with self._local_lock:
            held = self.locals.get(city)
            hour = snapshot.hours[0]
            # Số đo tại chỗ được áp lên đúng một bản tính của mô hình: có bản tính mới (kể cả do máy khác đẩy lên) thì tính lại.
            if held is not None and time.monotonic() - held[1] < LOCAL_TTL_S and held[2] is snapshot:
                return held[0]
            local = live_local.read(self.model(city), hour, source)
            self.locals[city] = (local, time.monotonic(), snapshot)
            return local

    def route_state(self, city: str):
        """Mức của từng tuyến lúc này sau số đo tại chỗ và báo cáo: (mức, tuyến đang được xác nhận ngập, báo cáo theo tuyến).

        None khi thành phố chưa có mô hình hoặc chưa tính được lần nào.
        """
        try:
            snapshot, _ = self.risk(city)
        except FileNotFoundError:
            return None
        if snapshot is None:
            return None
        model = self.model(city)
        local = self.local(city, snapshot)
        level = live_local.route_levels(model, local) if local is not None else model.levels(snapshot.hours[0])
        reported = live_reports.by_route(live_reports.active(settings.db_path(), city))
        level, confirmed = live_reports.apply(level, reported)
        return level, confirmed, reported

    def edge_route(self, city: str):
        """Với mỗi cạnh của mạng đường: dòng của tuyến chứa nó trong bảng tuyến. None nếu thành phố chưa có bảng gắn."""
        if city not in self.edge_routes:
            self.edge_routes[city] = floodcost.edge_route_rows(city, self.model(city).routes.route_id.to_numpy())
        return self.edge_routes[city]

    def route_at(self, city: str, lat: float, lon: float, max_m: float = 80.0):
        """Tuyến của mô hình tại một điểm: (dòng trong bảng tuyến, mã tuyến, tên). None nếu không có đường nào gần đó."""
        edge_route = self.edge_route(city)
        if edge_route is None:
            return None
        graph = self.graph(city)
        node, distance = graph.snap(lon, lat, "bike")
        if distance > max_m:
            return None
        rows = edge_route[np.flatnonzero((graph.u == node) | (graph.v == node))]
        rows = rows[rows >= 0]
        if not len(rows):
            return None
        routes = self.model(city).routes
        named = [r for r in rows if isinstance(routes["name"].iloc[int(r)], str)]
        row = int(named[0] if named else rows[0])
        name = routes["name"].iloc[row]
        return row, str(routes.route_id.iloc[row]), name if isinstance(name, str) else ""

    def flood_view(self, city: str):
        """Mức ngập trên từng cạnh của mạng đường, cho tìm đường tránh ngập. None khi thành phố chưa có đủ dữ liệu."""
        state = self.route_state(city)
        if state is None:
            return None
        edge_route = self.edge_route(city)
        if edge_route is None:
            return None
        level, confirmed, _ = state
        routes = self.model(city).routes
        history = (routes.history_rain | routes.history_tide).to_numpy(bool)
        return floodcost.FloodView(edge_route, np.asarray(level), history, routes["name"].fillna("").to_numpy(object), confirmed)
