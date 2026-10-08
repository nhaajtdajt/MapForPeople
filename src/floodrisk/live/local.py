"""Số đo tại chỗ quyết định tuyến nào có mức: trạm mưa quanh tuyến và mực nước Phú An.

Mô hình 2 chỉ cho một trạng thái mưa chung cả thành phố, tính từ dự báo thời tiết; ngày 08/10/2026 nó báo động trong khi
mưa to chỉ rơi ở ngoại thành, và bản đồ đỏ gần hết nội thành. Vì vậy trạng thái mưa của từng tuyến lấy từ trạm đo:
tuyến nằm trong RADIUS_M quanh trạm nhận trạng thái của trạm, tính bằng ngưỡng mm ghi ở GAUGE_WATCH và GAUGE_ALERT.
Công thức của Mô hình 2 không dùng cho trạm: nó được chỉnh trên mưa dự báo, đem mưa đo tại một điểm vào thì 14 mm trong
3 giờ đã thành "cảnh giác".
Ngưỡng mm (chốt tối 08/10, phương án E): 30 mm/giờ là mức "có thể ngập" (vàng) chứ không phải "ngập" — ngày 01/10 và 07/10
các trạm vượt 30 mm trùng với khu báo chí đưa tin ngập, nhưng tối 08/10 trạm Nguyễn Thiện Thuật đo 29,6 mm/giờ mà 8 camera
trong 1,7 km quanh đó chỉ thấy đường ướt. Mức "rất có thể ngập" (đỏ) đặt ở 50 mm/giờ hoặc 80 mm/3 giờ: con số đặt ra từ
hai ngày quan sát, chưa hiệu chỉnh; bộ ghi (tools/ghi_du_lieu.py) đang gom trạm, radar và ảnh camera mỗi 10 phút để chỉnh lại.
Bán kính RADIUS_M là cỡ một ô mưa dông; 5 km trước đây làm một trạm tô 2.215 tuyến nhóm A.
Tuyến không gần trạm nào đang mưa thì trạng thái mưa là yên, dù mô hình báo gì cho cả thành phố (quyết định của chủ dự án
ngày 08/10, thay cho quy tắc "chỉ nâng" ở ghi chú 11, QĐ4). Mực nước Phú An từ báo động 1 nâng trạng thái triều lên
cảnh giác, từ báo động 2 lên báo động. TIDE_WATCH_M, TIDE_ALERT_M do người làm web đặt, chưa hiệu chỉnh.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from floodrisk.model import levels

RADIUS_M = 3000.0
GAUGE_WATCH = (30.0, 50.0)  # mm trong giờ gần nhất, mm trong 3 giờ: đạt một trong hai là cảnh giác
GAUGE_ALERT = (50.0, 80.0)  # tương tự, cho báo động
TIDE_WATCH_M = 1.40  # báo động 1 tại Phú An
TIDE_ALERT_M = 1.50  # báo động 2 tại Phú An
MAX_GAUGE_LAG = timedelta(hours=2)  # trạm im lặng lâu hơn thế thì không dùng
VN = timezone(timedelta(hours=7))


@dataclass(frozen=True)
class Local:
    at: datetime
    gauges: list[dict]  # tên, tọa độ, mưa 1 giờ, 3 giờ, 24 giờ và trạng thái của từng trạm còn báo số
    tide: dict | None  # mực nước Phú An lúc này, cách biết, trạng thái
    rain_state: np.ndarray  # trạng thái mưa của từng tuyến sau khi xét trạm gần nó
    tide_state: int  # trạng thái triều của thành phố sau khi xét Phú An
    errors: list[str] = field(default_factory=list)


def gauge_inputs(hours: list[tuple[datetime, float]], now: datetime) -> dict | None:
    """Ba con số của một trạm: mưa giờ gần nhất, mưa 3 giờ lớn nhất trong 6 giờ qua, tổng 24 giờ qua. None nếu trạm im lặng."""
    past = [(t, v) for t, v in hours if t <= now + timedelta(minutes=5)]
    if not past or now - past[-1][0] > MAX_GAUGE_LAG:
        return None
    end = past[-1][0]
    series = pd.Series({t: float(v) for t, v in past}).sort_index()
    last6 = series[series.index > end - timedelta(hours=6)]
    grid = pd.date_range(end - timedelta(hours=5), end, freq="h")
    filled = last6.reindex(grid).fillna(0.0)  # giờ trạm không báo coi như không mưa
    return {"last_1h_mm": round(float(series.iloc[-1]), 1), "max_3h_mm": round(float(filled.rolling(3).sum().max()), 1),
            "total_24h_mm": round(float(series[series.index > end - timedelta(hours=24)].sum()), 1), "reported_at": end.isoformat()}


def gauge_state_of(last_1h_mm: float, max_3h_mm: float) -> int:
    if last_1h_mm >= GAUGE_ALERT[0] or max_3h_mm >= GAUGE_ALERT[1]:
        return levels.ALERT
    if last_1h_mm >= GAUGE_WATCH[0] or max_3h_mm >= GAUGE_WATCH[1]:
        return levels.WATCH
    return levels.QUIET


def tide_state_of(level_m: float) -> int:
    if level_m >= TIDE_ALERT_M:
        return levels.ALERT
    return levels.WATCH if level_m >= TIDE_WATCH_M else levels.QUIET


def _distance_m(lat, lon, lat0: float, lon0: float) -> np.ndarray:
    kx = 111_320.0 * np.cos(np.radians(lat0))
    return np.hypot((np.asarray(lon) - lon0) * kx, (np.asarray(lat) - lat0) * 110_540.0)


def routes_within(routes: pd.DataFrame, lat: float, lon: float, max_m: float, min_band: int = 2) -> np.ndarray:
    """Dòng của những tuyến có nhóm mưa từ `min_band` nằm trong `max_m` quanh một điểm (camera thấy gì thì nói cho cả khu nó nhìn)."""
    near = _distance_m(routes.lat.to_numpy(float), routes.lon.to_numpy(float), lat, lon) <= max_m
    return np.flatnonzero(near & (routes.band_rain.to_numpy() >= min_band))


def read(model, hour, source, now: datetime | None = None) -> Local:
    """Đọc trạm mưa và triều từ `source` (module hydro hoặc bản giả cùng ba hàm) rồi nâng trạng thái của `hour`."""
    now = now or datetime.now(VN)
    errors: list[str] = []
    rain_state = np.zeros(len(model.routes), np.uint8)  # yên, cho tới khi một trạm gần tuyến nói khác
    gauges: list[dict] = []
    try:
        lat, lon = model.routes.lat.to_numpy(float), model.routes.lon.to_numpy(float)
        for g in source.rain_gauges():
            inputs = gauge_inputs(source.gauge_hours(g), now)
            if inputs is None:
                continue
            state = gauge_state_of(inputs["last_1h_mm"], inputs["max_3h_mm"])
            gauges.append({"name": g["name"], "lat": g["lat"], "lon": g["lon"], **inputs, "state": state})
            if state > levels.QUIET:
                near = _distance_m(lat, lon, g["lat"], g["lon"]) <= RADIUS_M
                rain_state[near] = np.maximum(rain_state[near], state)
    except Exception as exc:  # cổng số liệu lỗi: không còn số đo, tạm dùng trạng thái chung của mô hình và báo lại
        errors.append(f"Chưa đọc được trạm mưa: {type(exc).__name__}: {exc}")
        rain_state = np.full(len(model.routes), hour.rain.state, np.uint8)
        gauges = []

    tide, tide_state = None, hour.tide.state
    try:
        point = source.tide_point(now)
        if point is not None:
            level_m, kind = float(point[0]), point[1]
            tide = {"station": "Phú An", "level_m": round(level_m, 2), "kind": kind, "state": tide_state_of(level_m)}
            tide_state = max(tide_state, tide["state"])
    except Exception as exc:
        errors.append(f"Chưa đọc được mực nước Phú An: {type(exc).__name__}: {exc}")
    return Local(now, gauges, tide, rain_state, int(tide_state), errors)


def route_levels(model, local: Local) -> np.ndarray:
    """Mức của từng tuyến sau khi xét số đo tại chỗ."""
    return levels.route_levels(model.bands_rain, model.bands_tide, local.rain_state, local.tide_state)
