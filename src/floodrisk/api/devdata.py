"""Dữ liệu mẫu cho phần web (spec 01, mục 2.1).

    python -m floodrisk.api.devdata data/sample [--stale]

Dựng trên `floodrisk.samples` (kế hoạch 01) và thêm: bảng ghi nhận ngập khớp cột `history`,
một kịch bản giả lập có nguy cơ tăng dần, `computed_at` là giờ hiện tại, và file đánh dấu `SAMPLE`.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from floodrisk import config
from floodrisk.api import fakes
from floodrisk.samples import make_sample

SYNTHETIC_ID = "sample-synthetic"
RISING = (0.2, 0.5, 0.95)  # hệ số mưa ở giờ 0, 1, 2: chỉ giờ 2 mới có đoạn mức cao
REPORTED_UNIT = 2
VN = timezone(timedelta(hours=7))


def vietnam_now() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(VN).replace(tzinfo=None, minute=0, second=0, microsecond=0))


def _observations(city: str, units: gpd.GeoDataFrame, scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, links = [], []
    by_id = units.set_index("unit_id")
    for score in scores.itertuples():
        if score.history <= 0:
            continue
        mid = by_id.loc[score.unit_id, "geometry"].interpolate(0.5, normalized=True)
        for k in range(score.history):
            year = int(score.last_year) - k
            last = k == 0
            depth = float(score.max_depth_cm) if last else max(5.0, float(score.max_depth_cm) - 10.0 * k)
            obs_id = f"{city}-sample-obs-{score.unit_id[-2:]}-{k}"
            rows.append({
                "obs_id": obs_id, "city": city, "source": "mẫu", "provenance": 5,
                "date": pd.Timestamp(f"{year}-10-15"), "year": float(year), "hour": 17.0,
                "lon": mid.x, "lat": mid.y, "loc_precision": "high" if score.exact else "medium",
                "flooded": True, "depth_cm": depth,
                "depth_class": 1.0 if depth < 10 else (2.0 if depth <= 30 else 3.0),
                "cause": "tide" if k % 2 else "rain", "street_name": by_id.loc[score.unit_id, "name"],
                "unit_id": score.unit_id, "evidence_url": f"https://example.com/mau/{obs_id}",
            })
            links.append({"obs_id": obs_id, "unit_id": score.unit_id, "exact": bool(score.exact),
                          "spread_m": 200.0 if score.exact else 1000.0})
    return pd.DataFrame(rows), pd.DataFrame(links)


def _rising_scenario(replay_folder: Path, scores: pd.DataFrame, now: pd.Timestamp) -> None:
    unit_ids = scores["unit_id"].to_numpy()
    s_rain = scores["s_rain"].to_numpy(float)
    frames = []
    for hour, factor in enumerate(RISING):
        risk = s_rain * factor
        frames.append(pd.DataFrame({
            "unit_id": unit_ids, "hour_offset": hour, "risk": risk, "level": fakes.to_level(risk).astype(int),
            "t_rain": factor, "t_tide": 0.0,
        }))
    table = pd.concat(frames, ignore_index=True)
    table["computed_at"] = now
    table["recorded"] = False
    table["reporters"] = 0
    table["reported_level"] = np.nan

    # Bốn người báo "ngập cao" ở đoạn REPORTED_UNIT, chỉ ở giờ 0 (bằng chứng chỉ áp dụng cho giờ hiện tại)
    at = datetime.now(timezone.utc)
    reports = [fakes.Report(f"sample-{k}", "high", at) for k in range(4)]
    row = int(np.flatnonzero((table["unit_id"] == unit_ids[REPORTED_UNIT]) & (table["hour_offset"] == 0))[0])
    result = fakes.apply_evidence(float(table.at[row, "risk"]), reports, at)
    table.at[row, "risk"] = result.risk
    table.at[row, "level"] = int(fakes.to_level(result.risk))
    table.at[row, "reporters"] = result.reporters
    table.at[row, "reported_level"] = float(result.reported_level)

    fakes.write_scenario(replay_folder, SYNTHETIC_ID, table, "Mưa tăng dần (giả lập)", "synthetic", now.isoformat())


def make_dev_data(root: Path, stale: bool = False) -> None:
    root = Path(root)
    now = vietnam_now()
    for city in config.CITIES:
        make_sample(root, city)
        folder = root / "processed" / city
        units = gpd.read_parquet(folder / "units.parquet")
        scores = pd.read_parquet(folder / "scores.parquet")

        observations, links = _observations(city, units, scores)
        observations.to_parquet(folder / "observations.parquet")
        links.to_parquet(folder / "obs_units.parquet")

        if not stale:
            risk = pd.read_parquet(folder / "risk.parquet")
            risk["computed_at"] = now
            risk.to_parquet(folder / "risk.parquet")

        _rising_scenario(folder / "replay", scores, now)

    (root / "processed" / "model_choice.json").write_text(
        json.dumps({"rain": "none", "tide": "none", "validated": ["hcm"]}), encoding="utf-8")
    (root / "processed" / "SAMPLE").write_text("", encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # đầu ra tiếng Việt khi chuyển hướng trên Windows
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target = Path(args[0]) if args else Path("data/sample")
    make_dev_data(target, stale="--stale" in sys.argv)
    print(f"Đã ghi dữ liệu mẫu cho {', '.join(config.CITIES)} vào {target}")
