"""Mức mưa và mức triều phải tính đúng như run_hourly.py của repo mô hình (commit 842da0a)."""
import math

import numpy as np
import pandas as pd
import pytest

from floodrisk.model import trigger

# Hệ số của rain_trigger.json trong mô hình final_2025-01-01.
CFG = {"selected_features": ["rain_max_3h_mm", "rain_total_mm"],
       "coef": [0.02283375645176585, 0.02851568232758494], "intercept": -0.0017792662252086328}
REFERENCE = pd.DataFrame({"rain_max_3h_mm": np.arange(1000) / 10, "rain_total_mm": np.arange(1000) / 10})  # 0,0 tới 99,9 mm


def _hourly(values: dict[str, float], start="2026-10-05 00:00", hours=96) -> pd.Series:
    index = pd.date_range(start, periods=hours, freq="h", tz=trigger.TZ)
    series = pd.Series(0.0, index=index)
    for when, mm in values.items():
        series[pd.Timestamp(when, tz=trigger.TZ)] = mm
    return series


def test_quantile_counts_reference_days_at_or_below_the_value():
    assert trigger.quantile(0.0, [0, 0, 1, 2]) == 0.5
    assert trigger.quantile(1.5, [0, 0, 1, 2]) == 0.75
    assert trigger.quantile(9.0, [0, 0, 1, 2]) == 1.0


def test_rain_trigger_is_bounded_because_quantiles_are_clipped():
    dry = trigger.rain_trigger(-1.0, -1.0, CFG, REFERENCE)  # dưới mọi ngày tham chiếu: vị trí 0, ép về 0,001
    wet = trigger.rain_trigger(500.0, 500.0, CFG, REFERENCE)  # trên mọi ngày tham chiếu: vị trí 1, ép về 0,999
    logit = math.log(0.999 / 0.001)
    assert dry == pytest.approx(1 / (1 + math.exp(logit * sum(CFG["coef"]) - CFG["intercept"])))
    assert wet == pytest.approx(1 / (1 + math.exp(-logit * sum(CFG["coef"]) - CFG["intercept"])))
    assert 0.41 < dry < 0.42 and 0.58 < wet < 0.59


def test_rain_trigger_rises_with_either_input():
    base = trigger.rain_trigger(20.0, 20.0, CFG, REFERENCE)
    assert trigger.rain_trigger(60.0, 20.0, CFG, REFERENCE) > base
    assert trigger.rain_trigger(20.0, 60.0, CFG, REFERENCE) > base


def test_rain_windows_take_the_wettest_three_hours_of_the_last_six_and_the_last_day():
    series = _hourly({"2026-10-07 14:00": 99.0,  # ngoài 6 giờ, trong 24 giờ của hai giờ đầu
                      "2026-10-08 08:00": 10.0, "2026-10-08 09:00": 20.0, "2026-10-08 10:00": 5.0, "2026-10-08 12:00": 1.0})
    now, plus1, plus2 = trigger.rain_windows(series, pd.Timestamp("2026-10-08 12:00", tz=trigger.TZ))
    assert now["rain_max_3h_mm"] == 35.0 and now["rain_total_mm"] == 135.0
    assert plus1["valid_time"] == pd.Timestamp("2026-10-08 13:00", tz=trigger.TZ)
    assert plus2["rain_max_3h_mm"] == 25.0  # cửa sổ 6 giờ đã trượt qua giờ 08:00
    assert plus2["rain_total_mm"] == 36.0  # và cửa sổ 24 giờ đã trượt qua trận 99 mm hôm trước


def test_rain_windows_refuse_a_short_series():
    series = _hourly({}, start="2026-10-08 09:00", hours=4)
    with pytest.raises(ValueError, match="Thiếu số liệu mưa"):
        trigger.rain_windows(series, pd.Timestamp("2026-10-08 12:00", tz=trigger.TZ))


def test_tide_trigger_is_half_at_the_95th_percentile_and_zero_without_a_tide_model():
    model = {"kind": "percentile", "climatology_q": list(np.linspace(3.0, 4.0, 201))}
    assert trigger.tide_trigger(3.95, model) == pytest.approx(0.5, abs=1e-6)
    assert trigger.tide_trigger(3.0, model) < 1e-15 and trigger.tide_trigger(4.5, model) > 0.9
    assert trigger.tide_trigger(4.5, {"kind": "zero"}) == 0.0


def test_grid_matches_the_model_repo():
    points = trigger.grid_points("ho_chi_minh")
    assert len(points) == 9 and points[0] == (10.55, 106.4363502282) and points[-1] == (11.05, 107.0)
    assert len(trigger.grid_points("da_nang")) == 6
