"""Số đo tại chỗ quyết định tuyến nào có mức: trạm mưa quanh tuyến và mực nước Phú An.

Mô hình 2 chỉ cho một trạng thái mưa chung cả thành phố, tính từ dự báo thời tiết; ngày 08/10/2026 nó báo động trong khi
mưa to chỉ rơi ở ngoại thành, và bản đồ đỏ gần hết nội thành. Vì vậy trạng thái mưa của từng tuyến lấy từ trạm đo:
tuyến nằm trong RADIUS_M quanh trạm nhận trạng thái của trạm, tính bằng ngưỡng mm ghi ở GAUGE_WATCH và GAUGE_ALERT.
Công thức của Mô hình 2 không dùng cho trạm: nó được chỉnh trên mưa dự báo, đem mưa đo tại một điểm vào thì 14 mm trong
3 giờ đã thành "cảnh giác".
Ngưỡng mm và bán kính chấm ngày 14/10 trên ba trận ngập do mưa có báo chí đưa tin (tối 01/10, trưa 06/10, chiều tối 07/10:
162 đoạn của 13 đường bị ngập) và một ngày mưa không ngập (08/10: trạm Nguyễn Thiện Thuật 29,6 mm/giờ, 8 camera quanh đó chỉ thấy
đường ướt). Quy tắc chiều 08/10 (15/30 mm, 5 km) tô 140/162 đoạn nhưng ngày 08/10 tô 312 km-giờ đỏ và 3.010 km-giờ vàng; quy
tắc tối 08/10 (30/50 mm, 3 km) không báo nhầm nhưng chỉ tô 97/162. Quy tắc này tô 129/162 (104 đỏ) và không tô gì ngày 08/10.
Ngưỡng đỏ 35 mm nằm giữa 29,6 mm (không ngập, 08/10) và 36 mm (trung tâm ngập, 06/10): nó được chọn trên chính các trận này,
chưa có trận nào khác để thử. Bộ ghi (tools/ghi_du_lieu.py) gom trạm, radar và ảnh camera để chấm lại khi có trận mưa mới.
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

RADIUS_M = 4000.0
# Trong FULL_RADIUS_M quanh trạm: đủ mức của trạm. Từ đó tới RADIUS_M: tối đa cảnh giác (vàng). Trước 16/10 cả vòng 4 km
# như nhau, nên một ngày bốn trạm cùng mưa to (07/10) tô đỏ 22% đường lớn nội thành. Chấm trên ba trận mưa có tin ngập
# (01, 06, 07/10): số đoạn đỏ giảm 62-72%, không trận nào mất chỗ ngập thật nào (07/10 vẫn 7/7, 06/10 4/4, 01/10 1/2).
FULL_RADIUS_M = 2000.0
GAUGE_WATCH = (30.0, 50.0)  # mm trong giờ gần nhất, mm trong 3 giờ: đạt một trong hai là cảnh giác
GAUGE_ALERT = (35.0, 80.0)  # tương tự, cho báo động
TIDE_WATCH_M = 1.40  # báo động 1 tại Phú An
TIDE_ALERT_M = 1.50  # báo động 2 tại Phú An (báo động 3 là 1,60 m)
# Triều càng cao thì càng nhiều tuyến ngập: mỗi bậc là (mực nước Phú An từ, (phần tuyến đầu bảng triều tô đỏ, phần có màu)).
# Chấm trên tuần 07-14/10/2026: các đường báo chí đưa tin ngập do triều (Trần Xuân Soạn, Phạm Hữu Lầu, Huỳnh Tấn Phát...)
# chỉ ngập khi Phú An từ 1,60 m. So với quy tắc cũ (từ 1,50 m tô nhóm A đỏ, nhóm B vàng, tức 20% số tuyến), bản đồ bị tô
# ít hơn 44% số km-giờ cả tuần, ít hơn 61% ở những giờ không có tin ngập, mà lúc đỉnh triều có tin ngập vẫn tô 91% đoạn
# đường được báo đưa tin (cũ 95%). Các bậc là số tròn đặt trước khi chấm, mới thử trên một đợt triều.
TIDE_STEPS = ((1.70, (.05, .20)), (1.60, (.05, .10)), (1.50, (.02, .05)), (1.40, (0.0, .02)))
MODEL_TIDE_EXTENT = {levels.QUIET: (0.0, 0.0), levels.WATCH: (0.0, .05), levels.ALERT: (.05, .20)}  # khi không có số Phú An: nhóm A, B như cũ
FORECAST_HOURS = 12  # dự báo triều Phú An: trước 24 giờ đoán đúng 12 trong 13 giờ vượt 1,40 m, không lần nào báo nhầm (07-14/10)
MAX_GAUGE_LAG = timedelta(hours=2)  # trạm im lặng lâu hơn thế thì không dùng
# Cổng tạo dòng của giờ vừa hết ngay đầu giờ, nhưng ở 14 trạm (Bến Cát, Thuận An, Củ Chi...) dòng đó là số 0 giữ chỗ, 19 tới 32
# phút sau mới có số thật (60 lượt ghi ngày 08/10: 21 trong 52 giờ-trạm có mưa; 13 trạm khác có số ngay). Không phân biệt được
# số 0 thật với số 0 giữ chỗ, nên trong SETTLE đầu giờ lấy số lớn hơn giữa dòng mới nhất và giờ trước. Giá phải trả: mưa tạnh
# thật thì trạng thái của trạm hạ chậm hơn, nhiều nhất bằng SETTLE.
SETTLE = timedelta(minutes=35)
VN = timezone(timedelta(hours=7))


@dataclass(frozen=True)
class Local:
    at: datetime
    gauges: list[dict]  # tên, tọa độ, mưa 1 giờ, 3 giờ, 24 giờ và trạng thái của từng trạm còn báo số
    tide: dict | None  # mực nước Phú An lúc này, cách biết, trạng thái
    rain_state: np.ndarray  # trạng thái mưa của từng tuyến sau khi xét trạm gần nó
    tide_state: int  # trạng thái triều của thành phố sau khi xét Phú An
    errors: list[str] = field(default_factory=list)
    tide_extent: tuple[float, float] = (0.0, 0.0)  # (phần tuyến đầu bảng triều tô đỏ, phần có màu), xem TIDE_STEPS
    tide_forecast: list[dict] = field(default_factory=list)  # Phú An từng giờ tới: giờ, mực nước, trạng thái


def gauge_inputs(hours: list[tuple[datetime, float]], now: datetime) -> dict | None:
    """Ba con số của một trạm: mưa giờ gần nhất đã có số, mưa 3 giờ lớn nhất trong 6 giờ qua, tổng 24 giờ qua. None nếu trạm im lặng.

    `reported_at` là giờ kết thúc của con số được dùng làm mưa giờ gần nhất (xem SETTLE).
    """
    past = [(t, v) for t, v in hours if t <= now + timedelta(minutes=5)]
    if not past or now - past[-1][0] > MAX_GAUGE_LAG:
        return None
    end = past[-1][0]
    series = pd.Series({t: float(v) for t, v in past}).sort_index()
    last6 = series[series.index > end - timedelta(hours=6)]
    grid = pd.date_range(end - timedelta(hours=5), end, freq="h")
    filled = last6.reindex(grid).fillna(0.0)  # giờ trạm không báo coi như không mưa
    last_mm, last_at = float(series.iloc[-1]), end
    before = series.get(end - timedelta(hours=1))
    if now - end < SETTLE and before is not None and float(before) > last_mm:
        last_mm, last_at = float(before), end - timedelta(hours=1)
    return {"last_1h_mm": round(last_mm, 1), "max_3h_mm": round(float(filled.rolling(3).sum().max()), 1),
            "total_24h_mm": round(float(series[series.index > end - timedelta(hours=24)].sum()), 1), "reported_at": last_at.isoformat()}


def gauge_state_of(last_1h_mm: float, max_3h_mm: float) -> int:
    if last_1h_mm >= GAUGE_ALERT[0] or max_3h_mm >= GAUGE_ALERT[1]:
        return levels.ALERT
    if last_1h_mm >= GAUGE_WATCH[0] or max_3h_mm >= GAUGE_WATCH[1]:
        return levels.WATCH
    return levels.QUIET


def tide_extent_of(level_m: float) -> tuple[float, float]:
    for step, extent in TIDE_STEPS:
        if level_m >= step:
            return extent
    return (0.0, 0.0)


def tide_state_of(level_m: float) -> int:
    if level_m >= TIDE_ALERT_M:
        return levels.ALERT
    return levels.WATCH if level_m >= TIDE_WATCH_M else levels.QUIET


def _distance_m(lat, lon, lat0: float, lon0: float) -> np.ndarray:
    kx = 111_320.0 * np.cos(np.radians(lat0))
    return np.hypot((np.asarray(lon) - lon0) * kx, (np.asarray(lat) - lat0) * 110_540.0)


def spread(lat, lon, lat0: float, lon0: float, state: int) -> np.ndarray:
    """Trạng thái mưa mà một trạm gán cho từng tuyến: đủ mức trong FULL_RADIUS_M, tối đa cảnh giác tới RADIUS_M, ngoài đó yên."""
    distance = _distance_m(lat, lon, lat0, lon0)
    out = np.where(distance <= FULL_RADIUS_M, state, min(state, levels.WATCH))
    return np.where(distance <= RADIUS_M, out, levels.QUIET).astype(np.uint8)


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
                rain_state = np.maximum(rain_state, spread(lat, lon, g["lat"], g["lon"], state))
    except Exception as exc:  # cổng số liệu lỗi: không còn số đo, tạm dùng trạng thái chung của mô hình và báo lại
        errors.append(f"Chưa đọc được trạm mưa: {type(exc).__name__}: {exc}")
        rain_state = np.full(len(model.routes), hour.rain.state, np.uint8)
        gauges = []

    # Có mực nước Phú An thì nó thay cho trạng thái triều của mô hình (triều thiên văn Vũng Tàu cho cả thành phố): số tại sông
    # Sài Gòn sát hơn, và mức tô màu theo bậc của nó (TIDE_STEPS).
    tide, tide_state, tide_extent, forecast = None, hour.tide.state, MODEL_TIDE_EXTENT[hour.tide.state], []
    try:
        point = source.tide_point(now)
        if point is not None:
            level_m, kind = float(point[0]), point[1]
            tide = {"station": "Phú An", "level_m": round(level_m, 2), "kind": kind, "state": tide_state_of(level_m)}
            tide_state, tide_extent = tide["state"], tide_extent_of(level_m)
            top = now.replace(minute=0, second=0, microsecond=0)
            for h in range(1, FORECAST_HOURS + 1):
                ahead = source.tide_point(top + timedelta(hours=h))
                if ahead is None:
                    break
                forecast.append({"time": (top + timedelta(hours=h)).isoformat(), "level_m": round(float(ahead[0]), 2),
                                 "state": tide_state_of(float(ahead[0]))})
    except Exception as exc:
        errors.append(f"Chưa đọc được mực nước Phú An: {type(exc).__name__}: {exc}")
    return Local(now, gauges, tide, rain_state, int(tide_state), errors, tide_extent, forecast)


def levels_of(model, rain_state, tide_extent: tuple[float, float]) -> np.ndarray:
    """Mức của từng tuyến: lớn hơn giữa mức do mưa (theo nhóm mưa) và mức do triều (theo thứ hạng triều và bậc của Phú An)."""
    return np.maximum(levels.cause_levels(model.bands_rain, rain_state), levels.extent_levels(model.tide_order, tide_extent))


def route_levels(model, local: Local) -> np.ndarray:
    """Mức của từng tuyến sau khi xét số đo tại chỗ."""
    return levels_of(model, local.rain_state, local.tide_extent)
