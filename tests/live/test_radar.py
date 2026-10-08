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
    rate = _rate_with_rain_at(10.80, 106.70, 21.0) + _rate_with_rain_at(10.90, 106.60, 13.0)  # 13 mm/giờ giờ chỉ là cảnh giác
    assert list(radar.states_at(spots[:, 0], spots[:, 1], rate)) == [levels.ALERT, levels.WATCH, levels.QUIET]


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


def test_gauges_use_millimetre_thresholds():
    assert local.gauge_state_of(14.0, 14.0) == levels.QUIET  # trước đây 14 mm trong 3 giờ đã là cảnh giác
    assert local.gauge_state_of(15.0, 15.0) == levels.WATCH and local.gauge_state_of(0.0, 30.0) == levels.WATCH
    assert local.gauge_state_of(30.0, 30.0) == levels.ALERT and local.gauge_state_of(5.0, 50.0) == levels.ALERT
