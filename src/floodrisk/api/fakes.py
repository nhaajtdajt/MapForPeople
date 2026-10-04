"""Bản giả của phần người AI chưa giao (spec 01, mục 2.3).

Cùng chữ ký với bản thật ở QĐKT mục 6, nhưng chỉ làm phép tính đơn giản để giao diện có thứ phản ứng.
Không dùng làm bằng chứng cho bất cứ điều gì về mô hình.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from floodrisk import config

FAKE_SUFFIX = " (bản giả)"
FLOOD_STATUSES = {"light": 1, "medium": 2, "high": 3}
MAX_AGE = timedelta(minutes=180)
COUNT_WINDOW = timedelta(minutes=30)
STEP_PER_REPORTER = 0.15
TIDE_T = {"none": 0.0, "significant": 0.45, "large": 0.75}


@dataclass(frozen=True)
class Report:
    reporter: str
    status: str  # "light" | "medium" | "high" | "clear"
    at: datetime  # có múi giờ, UTC
    official: bool = False


@dataclass(frozen=True)
class EvidenceResult:
    risk: float
    reporters: int
    reported_level: int | None  # 1 nhẹ, 2 vừa, 3 cao


def to_level(risk):
    risk = np.asarray(risk, dtype=float)
    return (risk >= config.LEVEL_MEDIUM).astype(int) + (risk >= config.LEVEL_HIGH).astype(int)


def apply_evidence(prior: float, reports: list[Report], now: datetime) -> EvidenceResult:
    latest: dict[str, Report] = {}
    for report in sorted(reports, key=lambda r: r.at):
        if now - report.at <= MAX_AGE:
            latest[report.reporter] = report  # báo cáo mới nhất của mỗi người ghi đè

    flooded = [r for r in latest.values() if r.status in FLOOD_STATUSES and now - r.at <= COUNT_WINDOW]
    cleared = [r for r in latest.values() if r.status == "clear"]

    risk = prior + STEP_PER_REPORTER * len(flooded) - STEP_PER_REPORTER * len(cleared)
    reported_level = None
    if flooded:
        votes = [FLOOD_STATUSES[r.status] for r in flooded]
        # mức nhiều người chọn nhất; hòa thì lấy mức cao hơn
        reported_level = max(set(votes), key=lambda level: (votes.count(level), level))
        if reported_level >= 3:
            risk = max(risk, config.LEVEL_HIGH)
        elif reported_level == 2:
            risk = max(risk, config.LEVEL_MEDIUM)
    return EvidenceResult(float(min(1.0, max(0.0, risk))), len(flooded), reported_level)


def run_hourly() -> list[str]:
    return []


def _scenario_id(kind: str, **params) -> str:
    digest = hashlib.sha1(json.dumps([kind, params], sort_keys=True, default=str).encode()).hexdigest()
    return f"{kind[:3]}-{digest[:8]}"


def write_scenario(folder: Path, scenario_id: str, frame: pd.DataFrame, label: str, kind: str, time: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(folder / f"{scenario_id}.parquet")
    index_file = folder / "index.json"
    index = json.loads(index_file.read_text(encoding="utf-8")) if index_file.exists() else []
    index = [row for row in index if row["id"] != scenario_id]  # chạy lại thì ghi đè, không thêm dòng trùng
    index.append({"id": scenario_id, "label": label, "kind": kind, "time": time,
                  "recorded_count": int(frame["recorded"].sum() // 3)})
    index_file.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def _risk_table(scores: pd.DataFrame, t_rain: float, t_tide: float, mask: np.ndarray, computed_at: pd.Timestamp,
                hours=(0, 1, 2)) -> pd.DataFrame:
    s_rain = scores["s_rain"].to_numpy(float) * mask
    s_tide = scores["s_tide"].to_numpy(float) * mask
    risk = 1 - (1 - s_rain * t_rain) * (1 - s_tide * t_tide)
    frames = []
    for hour in hours:
        frames.append(pd.DataFrame({
            "unit_id": scores["unit_id"].to_numpy(), "hour_offset": hour, "risk": risk,
            "level": to_level(risk).astype(int), "t_rain": t_rain * mask, "t_tide": t_tide * mask,
        }))
    table = pd.concat(frames, ignore_index=True)
    table["computed_at"] = computed_at
    table["recorded"] = False
    table["reporters"] = 0
    table["reported_level"] = np.nan
    return table


def make_synthetic(city: str, label: str, rain_3h_mm: float, rain_24h_mm: float | None = None,
                   cells: str = "all", tide: str = "none", n_reports: int = 0, seed: int = 0) -> str:
    scores = pd.read_parquet(config.scores_path(city))
    rng = np.random.default_rng(seed)
    mask = np.ones(len(scores))
    if cells == "random":
        mask = np.zeros(len(scores))
        mask[rng.choice(len(scores), size=max(1, len(scores) // 2), replace=False)] = 1.0
    now = pd.Timestamp(datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None, minute=0, second=0, microsecond=0))
    table = _risk_table(scores, min(1.0, rain_3h_mm / 100.0), TIDE_T[tide], mask, now)

    if n_reports > 0:
        at_now = datetime.now(timezone.utc)
        candidates = np.flatnonzero(table["hour_offset"].to_numpy() == 0)
        weights = table.loc[candidates, "risk"].to_numpy() + 0.05  # ưu tiên đoạn có nguy cơ lớn hơn
        picked = rng.choice(candidates, size=min(n_reports, len(candidates)), replace=False, p=weights / weights.sum())
        for row in picked:
            reports = [Report(f"gen-{row}-{k}", str(rng.choice(["light", "medium", "high", "clear"])), at_now)
                       for k in range(int(rng.integers(1, 6)))]
            result = apply_evidence(float(table.at[row, "risk"]), reports, at_now)
            table.loc[row, ["risk", "reporters"]] = [result.risk, result.reporters]
            table.at[row, "level"] = int(to_level(result.risk))
            table.at[row, "reported_level"] = np.nan if result.reported_level is None else float(result.reported_level)

    scenario_id = _scenario_id("synthetic", city=city, rain_3h_mm=rain_3h_mm, rain_24h_mm=rain_24h_mm,
                               cells=cells, tide=tide, n_reports=n_reports, seed=seed)
    write_scenario(config.replay_dir(city), scenario_id, table, label + FAKE_SUFFIX, "synthetic", now.isoformat())
    return scenario_id


def make_past_moment(city: str, when, label: str) -> str:
    when = pd.Timestamp(when)
    scores = pd.read_parquet(config.scores_path(city))
    t_rain = ((when.day * 7 + when.hour * 13) % 100) / 100.0  # cố định theo ngày giờ, không gọi mạng
    table = _risk_table(scores, t_rain, 0.0, np.ones(len(scores)), when)
    scenario_id = _scenario_id("past-moment", city=city, when=when.isoformat())
    write_scenario(config.replay_dir(city), scenario_id, table, label + FAKE_SUFFIX, "past-moment", when.isoformat())
    return scenario_id
