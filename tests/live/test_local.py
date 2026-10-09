"""Trạm mưa và mực nước Phú An chỉ được nâng mức của mô hình, và chỉ quanh trạm (ghi chú 11, QĐ4)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd

from floodrisk.api import floodcost
from floodrisk.live import local
from floodrisk.model import levels

VN = timezone(timedelta(hours=7))
NOW = datetime(2026, 10, 8, 14, 20, tzinfo=VN)
CFG = {"selected_features": ["rain_max_3h_mm", "rain_total_mm"],
       "coef": [0.02283375645176585, 0.02851568232758494], "intercept": -0.0017792662252086328}
REFERENCE = pd.DataFrame({"rain_max_3h_mm": np.arange(1000) / 10, "rain_total_mm": np.arange(1000) / 10})


def _model():
    # ba tuyến nhóm A theo mưa: hai tuyến sát trạm (cách vài trăm mét), một tuyến cách trạm khoảng 11 km
    routes = pd.DataFrame({"lat": [10.80, 10.801, 10.90], "lon": [106.70, 106.70, 106.70]})
    return SimpleNamespace(routes=routes, references={"ifs": REFERENCE}, rain_cfg=CFG, rain_limits=(0.5093524878214044, 0.5395158283435458),
                           bands_rain=np.array([2, 2, 2], np.uint8), bands_tide=np.array([0, 2, 0], np.uint8))


def _hour(rain=levels.QUIET, tide=levels.QUIET):
    return SimpleNamespace(rain=SimpleNamespace(state=rain), tide=SimpleNamespace(state=tide))


def _source(mm_per_hour: float, tide_m: float, last=NOW.replace(minute=0)):
    hours = [(last - timedelta(hours=k), mm_per_hour if k < 3 else 0.0) for k in range(30)][::-1]
    return SimpleNamespace(rain_gauges=lambda: [{"name": "Trạm thử", "lat": 10.80, "lon": 106.70}],
                           gauge_hours=lambda g: hours, tide_point=lambda t: (tide_m, "measured"))


def test_gauge_inputs_follow_the_model_windows():
    hours = [(NOW.replace(minute=0) - timedelta(hours=k), mm) for k, mm in enumerate([1.0, 20.0, 30.0, 0.0, 5.0, 0.0, 0.0, 99.0])][::-1]
    inputs = local.gauge_inputs(hours, NOW + timedelta(minutes=20))  # 14:40: số của giờ 13-14h đã chốt
    assert inputs["last_1h_mm"] == 1.0 and inputs["max_3h_mm"] == 51.0 and inputs["total_24h_mm"] == 155.0  # 99 mm nằm ngoài 6 giờ


def test_a_fresh_zero_does_not_hide_the_hour_before():
    # Bến Cát 08/10: dòng của giờ vừa hết hiện 0 lúc 16:01 và 16:11, tới 16:21 mới ra 34,6 mm
    top = NOW.replace(hour=16, minute=0)
    placeholder = [(top - timedelta(hours=1), 34.6), (top, 0.0)]
    early = local.gauge_inputs(placeholder, top + timedelta(minutes=10))
    assert early["last_1h_mm"] == 34.6 and early["reported_at"] == (top - timedelta(hours=1)).isoformat()
    settled = local.gauge_inputs(placeholder, top + timedelta(minutes=40))
    assert settled["last_1h_mm"] == 0.0 and settled["reported_at"] == top.isoformat()  # sau 35 phút thì số 0 là thật
    landed = local.gauge_inputs([(top - timedelta(hours=1), 5.0), (top, 34.6)], top + timedelta(minutes=10))
    assert landed["last_1h_mm"] == 34.6 and landed["reported_at"] == top.isoformat()  # số mới lớn hơn thì dùng ngay
    alone = local.gauge_inputs([(top, 0.0)], top + timedelta(minutes=10))
    assert alone["last_1h_mm"] == 0.0  # không có giờ trước để so


def test_routes_keep_their_state_while_the_new_hour_is_still_a_placeholder():
    top = NOW.replace(hour=16, minute=0)
    hours = [(top - timedelta(hours=k), mm) for k, mm in enumerate([0.0, 35.0, 0.0, 0.0])][::-1]  # 35 mm trong giờ 14-15h
    source = SimpleNamespace(rain_gauges=lambda: [{"name": "Trạm thử", "lat": 10.80, "lon": 106.70}],
                             gauge_hours=lambda g: hours, tide_point=lambda t: (0.5, "measured"))
    early = local.read(_model(), _hour(), source, top + timedelta(minutes=10))
    assert list(early.rain_state) == [levels.WATCH, levels.WATCH, levels.QUIET]  # trước đây tụt về yên ngay 16:01
    settled = local.read(_model(), _hour(), source, top + timedelta(minutes=40))
    assert list(settled.rain_state) == [levels.QUIET] * 3


def test_silent_gauge_is_ignored():
    hours = [(NOW - timedelta(hours=5), 80.0)]
    assert local.gauge_inputs(hours, NOW) is None


def test_routes_within_picks_flood_prone_routes_inside_the_radius():
    routes = pd.DataFrame({"lat": [10.80, 10.802, 10.802, 10.85], "lon": [106.70, 106.70, 106.70, 106.70], "band_rain": [2, 2, 1, 2]})
    assert list(local.routes_within(routes, 10.80, 106.70, 500.0)) == [0, 1]  # dòng 2 là nhóm B, dòng 3 cách 5,5 km


def test_heavy_rain_at_a_gauge_raises_only_routes_within_the_radius():
    found = local.read(_model(), _hour(), _source(33.0, 0.9), NOW)  # 99 mm trong 3 giờ tại trạm: báo động
    assert found.gauges[0]["state"] == levels.ALERT and found.errors == []
    assert list(found.rain_state) == [2, 2, 0]
    assert list(local.route_levels(_model(), found)) == [2, 2, 0]


def test_routes_follow_the_gauges_not_the_citywide_forecast():
    # Mô hình báo động cả thành phố nhưng trạm gần tuyến không mưa: tuyến không có trạng thái mưa (quyết định ngày 08/10).
    found = local.read(_model(), _hour(rain=levels.ALERT), _source(0.0, 0.9), NOW)
    assert list(found.rain_state) == [0, 0, 0] and list(local.route_levels(_model(), found)) == [0, 0, 0]


def test_phu_an_level_raises_the_tide_state_at_alarm_levels():
    assert [local.tide_state_of(m) for m in (1.39, 1.40, 1.49, 1.50, 1.8)] == [0, 1, 1, 2, 2]
    found = local.read(_model(), _hour(), _source(0.0, 1.52), NOW)
    assert found.tide_state == levels.ALERT and found.tide["level_m"] == 1.52
    assert list(local.route_levels(_model(), found)) == [0, 2, 0]  # chỉ tuyến thuộc nhóm theo triều lên mức


def test_a_failing_source_keeps_the_model_levels_and_reports_the_error():
    def broken():
        raise RuntimeError("cổng số liệu lỗi")

    source = SimpleNamespace(rain_gauges=broken, gauge_hours=None, tide_point=lambda t: broken())
    found = local.read(_model(), _hour(rain=levels.WATCH), source, NOW)
    assert list(found.rain_state) == [1, 1, 1] and found.tide is None and len(found.errors) == 2


def test_flood_cost_slows_history_routes_most_and_reports_exposure():
    view = floodcost.FloodView(edge_route=np.array([0, 1, 2, -1]), level=np.array([2, 1, 1]),
                               history=np.array([False, False, True]), names=np.array(["A", "", "C"], object))
    assert list(floodcost.slow_factors(view)) == [floodcost.MODEL_HIGH_FACTOR, floodcost.MODEL_MEDIUM_FACTOR, floodcost.HISTORY_FACTOR, 1.0]
    seen = floodcost.exposure(np.array([0, 1, 2, 3]), np.array([100.0, 200.0, 300.0, 400.0]), view)
    assert (seen["high_m"], seen["medium_m"], seen["history_m"]) == (100, 500, 300)
    assert seen["segments"][0] == {"name": "C", "level": 1, "basis": "history", "length_m": 300}
    assert {s["name"] for s in seen["segments"]} == {"A", "C", "Đường chưa có tên"}
