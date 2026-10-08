"""Nhóm tuyến và mức nguy cơ phải theo đúng quy tắc của repo mô hình (run_hourly.py, commit 842da0a)."""
import numpy as np

from floodrisk.model import levels


def test_top_five_percent_is_band_a_and_next_fifteen_is_band_b():
    score = np.linspace(1.0, 0.0, 100)  # tuyến 0 điểm cao nhất
    bands = levels.route_bands(score, score, np.ones(100, bool))
    assert list(bands[:5]) == [2] * 5 and list(bands[5:20]) == [1] * 15 and not bands[20:].any()


def test_bands_are_ranked_only_among_masked_routes():
    score = np.linspace(1.0, 0.0, 100)
    mask = np.arange(100) >= 50  # chỉ 50 tuyến điểm thấp được xếp
    bands = levels.route_bands(score, score, mask)
    assert not bands[:50].any() and (bands == 2).sum() == 3 and (bands == 1).sum() == 7  # trần 5% và 20% của 50
    assert list(np.flatnonzero(bands == 2)) == [50, 51, 52]


def test_equal_scores_are_split_by_tie_then_by_row_order():
    score = np.ones(40)
    tie = np.zeros(40)
    tie[30] = 1.0
    bands = levels.route_bands(score, tie, np.ones(40, bool))
    assert list(np.flatnonzero(bands == 2)) == [0, 30]  # 5% của 40 là 2 tuyến: tuyến có tie lớn hơn, rồi dòng đầu


def test_live_bands_rank_every_route_on_the_hybrid_score():
    score = np.linspace(0.0, 1.0, 200, dtype=np.float32)
    bands = levels.live_bands(score)
    assert (bands == 2).sum() == 10 and (bands == 1).sum() == 30 and bands[-1] == 2 and bands[0] == 0


def test_day_state_uses_closed_lower_bounds():
    assert [levels.day_state(t, 0.5, 0.6) for t in (0.49, 0.5, 0.59, 0.6, 0.9)] == [0, 1, 1, 2, 2]


def test_levels_follow_the_two_factor_rule():
    rain = np.array([2, 1, 0, 0], np.uint8)  # nhóm theo mưa: A, B, C, C
    tide = np.array([0, 0, 2, 1], np.uint8)  # nhóm theo triều: C, C, A, B
    quiet, watch, alert = levels.QUIET, levels.WATCH, levels.ALERT
    assert list(levels.route_levels(rain, tide, quiet, quiet)) == [0, 0, 0, 0]
    assert list(levels.route_levels(rain, tide, watch, quiet)) == [1, 0, 0, 0]  # cảnh giác: chỉ nhóm A lên vừa
    assert list(levels.route_levels(rain, tide, alert, quiet)) == [2, 1, 0, 0]  # báo động: A lên cao, B lên vừa
    assert list(levels.route_levels(rain, tide, quiet, alert)) == [0, 0, 2, 1]
    assert list(levels.route_levels(rain, tide, watch, alert)) == [1, 0, 2, 1]  # lấy mức lớn hơn giữa hai nguyên nhân
