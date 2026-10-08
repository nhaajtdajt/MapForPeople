"""Báo ngập của người dùng và của camera: lưu lại, rồi nâng hoặc hạ mức của đúng tuyến đó (ghi chú 11, QĐ4).

Quy tắc đếm là của repo mô hình (`report_evidence.py`): mỗi người một báo cáo cho mỗi tuyến trong 30 phút, mức hiển thị
là mức được báo nhiều nhất, hòa thì lấy mức nặng hơn. Tác động lên mức của tuyến:
- đa số báo ngập cao (trên 30 cm): tuyến lên mức cao;
- đa số báo ngập vừa (10 tới 30 cm) hoặc ngập không rõ độ sâu: tuyến lên ít nhất mức vừa;
- đa số báo không ngập: tuyến hạ một bậc;
- báo ngập nhẹ (dưới 10 cm): không đổi mức, chỉ hiện trên bản đồ.
Báo cáo hết hiệu lực sau ACTIVE_MINUTES phút.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from floodrisk.model import report_evidence

ACTIVE_MINUTES = 90
DEPTH_CM = {"light": 5.0, "medium": 20.0, "high": 40.0}  # giá trị đại diện của ba lớp độ sâu, để dùng hàm của repo mô hình
STATUSES = ("flooded", "clear")
SCHEMA = """CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT, city TEXT NOT NULL, route_row INTEGER NOT NULL, route_id TEXT NOT NULL,
    lat REAL NOT NULL, lon REAL NOT NULL, status TEXT NOT NULL, depth TEXT, user_id TEXT NOT NULL,
    source TEXT NOT NULL, note TEXT, at TEXT NOT NULL)"""


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute(SCHEMA)
    return db


def add(path: Path, city: str, route_row: int, route_id: str, lat: float, lon: float, status: str, depth: str | None,
        user_id: str, source: str = "user", note: str | None = None, at: datetime | None = None) -> dict:
    if status not in STATUSES:
        raise ValueError("Trạng thái phải là flooded (ngập) hoặc clear (không ngập)")
    if depth is not None and depth not in DEPTH_CM:
        raise ValueError("Độ sâu phải là light, medium hoặc high")
    at = at or datetime.now(timezone.utc)
    with _connect(path) as db:
        cursor = db.execute(
            "INSERT INTO reports (city, route_row, route_id, lat, lon, status, depth, user_id, source, note, at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (city, int(route_row), route_id, lat, lon, status, depth if status == "flooded" else None, user_id, source, note,
             at.astimezone(timezone.utc).isoformat()))
        return {"id": cursor.lastrowid, "city": city, "route_row": int(route_row), "route_id": route_id, "lat": lat, "lon": lon,
                "status": status, "depth": depth if status == "flooded" else None, "source": source, "note": note,
                "at": at.astimezone(timezone.utc).isoformat()}


def active(path: Path, city: str, now: datetime | None = None) -> list[dict]:
    """Các báo cáo còn hiệu lực của một thành phố, mới nhất trước."""
    if not path.exists():
        return []
    now = now or datetime.now(timezone.utc)
    since = (now - timedelta(minutes=ACTIVE_MINUTES)).astimezone(timezone.utc).isoformat()
    with _connect(path) as db:
        rows = db.execute("SELECT * FROM reports WHERE city = ? AND at >= ? AND at <= ? ORDER BY at DESC",
                          (city, since, now.astimezone(timezone.utc).isoformat())).fetchall()
    return [dict(r) for r in rows]


def by_route(reports: list[dict], now: datetime | None = None) -> dict[int, dict]:
    """Với mỗi tuyến đang có báo cáo: mức được báo nhiều nhất (theo quy tắc của repo mô hình), số báo cáo, lần báo gần nhất."""
    now = now or datetime.now(timezone.utc)
    grouped: dict[int, list[dict]] = {}
    for r in reports:
        grouped.setdefault(r["route_row"], []).append(r)
    out = {}
    for row, items in grouped.items():
        records = [{"user_id": r["user_id"], "route_id": r["route_id"], "timestamp": r["at"],
                    "status": "flooded" if r["status"] == "flooded" else "not_flooded",
                    "depth_cm": DEPTH_CM.get(r["depth"]) if r["depth"] else None} for r in items]
        shown = report_evidence.displayed_level(records, now)
        if shown is None:
            continue
        out[row] = {"shown": shown, "count": len(report_evidence.deduplicate_user_route(records)), "last_at": max(r["at"] for r in items),
                    "sources": sorted({r["source"] for r in items})}
    return out


def apply(level: np.ndarray, routes: dict[int, dict]) -> tuple[np.ndarray, np.ndarray]:
    """Mức của từng tuyến sau khi xét báo cáo, và những tuyến đang được xác nhận ngập vừa trở lên."""
    level = np.array(level, np.uint8)
    confirmed = np.zeros(len(level), bool)
    for row, info in routes.items():
        if info["shown"] == "high":
            level[row], confirmed[row] = 2, True
        elif info["shown"] in ("moderate", "unknown"):
            level[row], confirmed[row] = max(int(level[row]), 1), True
        elif info["shown"] == "none":
            level[row] = max(int(level[row]) - 1, 0)
    return level, confirmed
