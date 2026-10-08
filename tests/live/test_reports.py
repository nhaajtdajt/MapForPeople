"""Báo ngập nâng hoặc hạ mức của đúng tuyến được báo, theo quy tắc đếm của repo mô hình (ghi chú 11, QĐ4)."""
from datetime import datetime, timedelta, timezone

import numpy as np

from floodrisk.live import reports

NOW = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)


def _add(db, row, status, depth=None, user="u1", minutes_ago=5, source="user"):
    return reports.add(db, "hcm", row, f"r{row}", 10.78, 106.70, status, depth, user, source=source, at=NOW - timedelta(minutes=minutes_ago))


def test_reports_expire_and_are_listed_newest_first(tmp_path):
    db = tmp_path / "reports.sqlite"
    _add(db, 1, "flooded", "high", minutes_ago=200)  # quá cũ
    _add(db, 1, "flooded", "medium", minutes_ago=30)
    _add(db, 2, "clear", minutes_ago=5)
    found = reports.active(db, "hcm", NOW)
    assert [(r["route_row"], r["status"], r["depth"]) for r in found] == [(2, "clear", None), (1, "flooded", "medium")]
    assert reports.active(db, "danang", NOW) == [] and reports.active(tmp_path / "missing.sqlite", "hcm", NOW) == []


def test_one_user_counts_once_per_route_and_the_most_reported_level_wins(tmp_path):
    db = tmp_path / "reports.sqlite"
    for minutes in (20, 10, 2):  # cùng một người bấm ba lần trong 30 phút: tính một
        _add(db, 7, "flooded", "high", user="u1", minutes_ago=minutes)
    _add(db, 7, "flooded", "medium", user="u2")
    _add(db, 7, "flooded", "medium", user="u3")
    summary = reports.by_route(reports.active(db, "hcm", NOW), NOW)
    assert summary[7]["shown"] == "moderate" and summary[7]["count"] == 3 and summary[7]["sources"] == ["user"]


def test_reports_change_only_the_reported_routes(tmp_path):
    db = tmp_path / "reports.sqlite"
    _add(db, 0, "flooded", "high")  # mức thấp -> cao
    _add(db, 1, "flooded", "medium")  # mức thấp -> vừa
    _add(db, 2, "flooded", "light")  # ngập nhẹ: không đổi mức
    _add(db, 3, "clear")  # mức cao -> vừa
    _add(db, 4, "flooded", None, source="camera")  # ngập không rõ độ sâu -> ít nhất mức vừa
    level, confirmed = reports.apply(np.array([0, 0, 0, 2, 0, 1], np.uint8), reports.by_route(reports.active(db, "hcm", NOW), NOW))
    assert list(level) == [2, 1, 0, 1, 1, 1]
    assert list(confirmed) == [True, True, False, False, True, False]


def test_bad_status_or_depth_is_refused(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        _add(tmp_path / "r.sqlite", 0, "maybe")
    with pytest.raises(ValueError):
        _add(tmp_path / "r.sqlite", 0, "flooded", "deep")
