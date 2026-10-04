"""Những điều phần web dựa vào ở mã của người AI (spec 01, mục 2.4).

Chạy trên bản mà `ports` chọn: bản giả hôm nay, bản thật khi người AI giao. Nếu bộ này trượt sau khi
gộp bản thật thì chỗ lệch nằm ở đường nối và phải báo cho người AI.
"""
import json
from datetime import datetime, timedelta, timezone

import geopandas  # noqa: F401  (đảm bảo parquet đọc được)
import pandas as pd

from floodrisk import config, contracts
from floodrisk.api import ports

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)


def _report(reporter, status, minutes_ago=5):
    return ports.Report(reporter, status, NOW - timedelta(minutes=minutes_ago))


def test_no_reports_leaves_prior_untouched():
    result = ports.apply_evidence(0.2, [], NOW)
    assert result.risk == 0.2 and result.reporters == 0 and result.reported_level is None


def test_four_reporters_of_high_flood_reach_high_level():
    reports = [_report(f"u{k}", "high", 10) for k in range(4)]
    result = ports.apply_evidence(0.1, reports, NOW)
    assert int(ports.to_level(result.risk)) == 2 and result.reporters == 4 and result.reported_level == 3


def test_same_reporter_counts_once_and_latest_wins():
    reports = [_report("u1", "light", 20), _report("u1", "high", 5)]
    result = ports.apply_evidence(0.1, reports, NOW)
    assert result.reporters == 1 and result.reported_level == 3


def test_report_older_than_three_hours_has_no_effect():
    result = ports.apply_evidence(0.3, [_report("u1", "high", 181)], NOW)
    assert result.risk == 0.3 and result.reporters == 0


def test_clear_report_never_raises_risk():
    result = ports.apply_evidence(0.4, [_report("u1", "clear", 5)], NOW)
    assert result.risk <= 0.4 and result.reporters == 0


def test_levels_use_config_thresholds():
    levels = ports.to_level([0.0, config.LEVEL_MEDIUM - 1e-6, config.LEVEL_MEDIUM, config.LEVEL_HIGH, 1.0])
    assert list(levels) == [0, 0, 1, 2, 2]


def test_synthetic_scenario_is_valid_idempotent_and_seeded(data):
    first = ports.make_synthetic("hcm", "Thử", rain_3h_mm=60, cells="random", n_reports=3, seed=7)
    again = ports.make_synthetic("hcm", "Thử", rain_3h_mm=60, cells="random", n_reports=3, seed=7)
    assert isinstance(first, str) and first == again

    folder = config.replay_dir("hcm")
    frame = pd.read_parquet(folder / f"{first}.parquet")
    contracts.validate(frame, contracts.REPLAY, "replay")
    assert sorted(frame["hour_offset"].unique()) == [0, 1, 2]

    index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    assert [row["id"] for row in index].count(first) == 1
    assert next(row for row in index if row["id"] == first)["kind"] == "synthetic"


def test_more_rain_never_lowers_any_level(data):
    levels = []
    for mm in (0, 10, 30, 50, 80, 120):
        scenario = ports.make_synthetic("hcm", f"{mm} mm", rain_3h_mm=mm)
        frame = pd.read_parquet(config.replay_dir("hcm") / f"{scenario}.parquet")
        levels.append(frame[frame["hour_offset"] == 0].set_index("unit_id")["level"])
    for lower, higher in zip(levels, levels[1:]):
        assert (higher >= lower).all()


def test_past_moment_scenario_is_valid(data):
    scenario = ports.make_past_moment("hcm", "2026-10-03 18:00", "Chiều qua")
    frame = pd.read_parquet(config.replay_dir("hcm") / f"{scenario}.parquet")
    contracts.validate(frame, contracts.REPLAY, "replay")
    index = json.loads((config.replay_dir("hcm") / "index.json").read_text(encoding="utf-8"))
    assert next(row for row in index if row["id"] == scenario)["kind"] == "past-moment"


def test_hourly_returns_a_list():
    assert isinstance(ports.run_hourly(), list)
