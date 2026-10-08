"""Radar: đổi cường độ mưa của giờ qua thành trạng thái tại từng vị trí, và trạm đo dùng ngưỡng mm."""
import numpy as np

from floodrisk.live import local, radar
from floodrisk.model import levels


def test_rain_rate_rises_with_the_colour_level_and_is_zero_without_echo():
    assert radar.RATE_MM_H[0] == 0 and (np.diff(radar.RATE_MM_H) > 0).all()
    assert 2 < radar.RATE_MM_H[5] < 4 and 40 < radar.RATE_MM_H[9] < 60  # 30 dBZ khoảng 3 mm/giờ, 50 dBZ khoảng 50 mm/giờ


def _rate_with_rain_at(lat, lon, mm_h, size=2310):
    rate = np.zeros((size, size), np.float32)
    east = (lon - radar.SITE[1]) * 111.32 * np.cos(np.radians(radar.SITE[0]))
    north = (lat - radar.SITE[0]) * 110.54
    col = int(round(size // 2 + east / radar.KM_PER_PX)) + radar.SHIFT_PX[0]
    row = int(round(size // 2 - north / radar.KM_PER_PX)) + radar.SHIFT_PX[1]
    rate[row - 3:row + 4, col - 3:col + 4] = mm_h
    return rate


def test_states_follow_the_two_radar_thresholds_at_the_right_place():
    spots = np.array([[10.80, 106.70], [10.90, 106.60], [10.75, 106.65]])
    rate = _rate_with_rain_at(10.80, 106.70, 36.0) + _rate_with_rain_at(10.90, 106.60, 21.0)  # 21 trên thang radar ≈ 30 mm trạm: cảnh giác
    assert list(radar.states_at(spots[:, 0], spots[:, 1], rate)) == [levels.ALERT, levels.WATCH, levels.QUIET]
    assert radar.states_at([10.80], [106.70], _rate_with_rain_at(10.80, 106.70, 27.0))[0] == levels.WATCH  # ≈ 38 mm trạm: chưa phải báo động


def test_points_next_to_the_radar_or_outside_the_image_are_never_flagged():
    rate = np.full((2310, 2310), 99.0, np.float32)
    lat = np.array([radar.SITE[0] + 0.01, 25.0])  # cách trạm 1 km; ngoài ảnh
    lon = np.array([radar.SITE[1], 106.7])
    assert list(radar.states_at(lat, lon, rate)) == [0, 0]


def test_hourly_rate_averages_the_hour_and_smooths_single_pixels():
    wet = np.zeros((200, 200), np.uint8)
    wet[100, 100] = 9  # một điểm lẻ rất mạnh trong một ảnh
    rate = radar.hourly_rate([wet, np.zeros_like(wet), np.zeros_like(wet), np.zeros_like(wet)])
    assert rate[100, 100] < 1.0 and rate.max() < 1.0  # không đủ để thành cảnh giác


def test_dry_background_is_subtracted_before_the_thresholds(tmp_path):
    wet = np.zeros((60, 60), np.uint8)
    wet[20:40, 20:40] = 8  # một vùng mưa đều trong cả bốn ảnh
    plain = radar.hourly_rate([wet] * 4)
    assert plain[30, 30] > 20
    clutter = np.full((60, 60), plain[30, 30] - 1.0, np.float32)  # nền khô cao gần bằng: như cảng Tân Thuận
    assert abs(radar.hourly_rate([wet] * 4, clutter)[30, 30] - 1.0) < 1e-4
    assert radar.hourly_rate([wet] * 4, np.full((60, 60), 99.0, np.float32)).max() == 0.0  # không bao giờ âm
    assert radar.dry_background(tmp_path / "khong_co.npz") is None
    radar.save_background(np.full((60, 60), 2.3, np.float32), tmp_path / "nen.npz", images=3)
    loaded = radar.dry_background(tmp_path / "nen.npz")
    assert loaded.shape == (60, 60) and abs(loaded[0, 0] - 2.25) < 1e-6  # lượng tử 0,25 mm/giờ


def test_gauges_use_millimetre_thresholds():
    assert local.gauge_state_of(29.6, 29.6) == levels.QUIET  # tối 08/10: 29,6 mm/giờ, camera quanh trạm chỉ thấy đường ướt
    assert local.gauge_state_of(30.0, 30.0) == levels.WATCH and local.gauge_state_of(0.0, 50.0) == levels.WATCH
    assert local.gauge_state_of(50.0, 50.0) == levels.ALERT and local.gauge_state_of(5.0, 80.0) == levels.ALERT
    assert local.gauge_state_of(49.0, 79.0) == levels.WATCH
