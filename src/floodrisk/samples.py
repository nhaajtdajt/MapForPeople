from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString

from floodrisk.config import CITIES, LEVEL_HIGH, LEVEL_MEDIUM

STEP = 0.0018  # khoảng 200 m
REPLAY_DATE = "2024-10-18"
TRIGGER = {
    "rain": {"features": ["r3max", "r24"], "intercept": -9.06, "coef": [2.44, 0.0], "fitted": False,
             "cuts": {"medium": 0.3, "high": 0.7}, "cut_mm": {"medium": 28.0, "high": 57.0}},
    "tide": {"features": ["tide_max"], "intercept": -3.0, "coef": [3.0], "fitted": False,
             "cuts": {"medium": 0.5, "high": 0.8}, "cut_mm": None},
}


def _levels(risk: np.ndarray) -> np.ndarray:
    return (risk >= LEVEL_MEDIUM).astype(int) + (risk >= LEVEL_HIGH).astype(int)


def make_sample(root: Path, city: str = "hcm", n: int = 4, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    lon0, lat0 = CITIES[city].center
    span = (n - 1) * STEP
    streets: list[tuple[str, LineString]] = []
    for i in range(n):
        y = lat0 + i * STEP
        streets.append((f"Đường Mẫu Ngang {i + 1}", LineString([(lon0, y), (lon0 + span, y)])))
        x = lon0 + i * STEP
        streets.append((f"Đường Mẫu Dọc {i + 1}", LineString([(x, lat0), (x, lat0 + span)])))
    k = len(streets)
    unit_ids = [f"{city}-sample{j:02d}" for j in range(k)]

    units = gpd.GeoDataFrame(
        {
            "unit_id": unit_ids,
            "parent_id": [f"{city}-p-sample{j:02d}" for j in range(k)],
            "city": city,
            "name": [name for name, _ in streets],
            "road_class": "residential",
            "road_rank": 1,
            "length_m": 600.0,
            "is_bridge": False,
            "is_tunnel": False,
            "rain_cell": 0,
            "elev_min": rng.uniform(0.5, 3.0, k),
            "elev_mean": rng.uniform(1.0, 3.5, k),
            "tpi_300": rng.normal(0.0, 0.3, k),
            "tpi_1000": rng.normal(0.0, 0.5, k),
            "dist_water_m": rng.uniform(20.0, 800.0, k),
            "built_frac_200": rng.uniform(0.5, 1.0, k),
        },
        geometry=[geom for _, geom in streets],
        crs=4326,
    )

    s_rain = np.linspace(0.05, 0.95, k)
    exact = np.array([j % 2 == 0 for j in range(k)])
    scores = pd.DataFrame({
        "unit_id": unit_ids,
        "s_rain": s_rain,
        "s_tide": s_rain[::-1].copy(),
        "basis": ["history" if j >= 2 else "model" for j in range(k)],
        "exact": exact,
        "loc_weight": np.where(exact, 1.0, 0.3),
        "history": [max(0, j - 1) for j in range(k)],
        "max_depth_cm": [None, None, 15.0, 20.0, 25.0, 30.0, 40.0, 60.0],
        "last_year": [None, None, 2018.0, 2019.0, 2022.0, 2023.0, 2024.0, 2025.0],
    })

    def frame(hour: int, risk: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame({"unit_id": unit_ids, "hour_offset": hour, "risk": risk, "level": _levels(risk),
                             "t_rain": risk / np.maximum(s_rain, 1e-9), "t_tide": 0.0})

    risk = pd.concat([frame(hour, s_rain * t) for hour, t in enumerate((0.9, 0.6, 0.3))], ignore_index=True)
    risk["computed_at"] = pd.Timestamp("2026-10-04 08:00:00")

    replay = pd.concat([frame(hour, s_rain * 0.95) for hour in (0, 1, 2)], ignore_index=True)
    replay["computed_at"] = pd.Timestamp(REPLAY_DATE)
    replay["recorded"] = replay["unit_id"].isin([unit_ids[5], unit_ids[7]])
    replay["reporters"] = 0
    replay["reported_level"] = np.nan

    cells = pd.DataFrame({"city": [city], "cell_id": [0], "lon": [lon0], "lat": [lat0]})

    # Mạng đường mẫu: 16 nút ở các giao lộ, mỗi khúc 200 m giữa hai nút kề nhau là hai cạnh ngược chiều.
    nodes = pd.DataFrame([{"node_id": r * n + c, "lon": lon0 + c * STEP, "lat": lat0 + r * STEP}
                          for r in range(n) for c in range(n)])
    edge_rows, link_rows = [], []

    def add_street_piece(a: int, b: int, unit_id: str) -> None:
        for u, v in ((a, b), (b, a)):
            edge_id = len(edge_rows)
            start, end = nodes.iloc[u], nodes.iloc[v]
            edge_rows.append({"edge_id": edge_id, "u": u, "v": v, "length_m": 200.0, "highway": "residential",
                              "geometry": LineString([(start["lon"], start["lat"]), (end["lon"], end["lat"])])})
            link_rows.append({"edge_id": edge_id, "unit_id": unit_id, "length_m": 200.0})

    for r in range(n):
        for c in range(n - 1):
            add_street_piece(r * n + c, r * n + c + 1, unit_ids[2 * r])  # đường ngang thứ r
    for c in range(n):
        for r in range(n - 1):
            add_street_piece(r * n + c, (r + 1) * n + c, unit_ids[2 * c + 1])  # đường dọc thứ c
    edges = gpd.GeoDataFrame(edge_rows, geometry="geometry", crs=4326)
    edge_units = pd.DataFrame(link_rows)

    out = Path(root) / "processed" / city
    (out / "model").mkdir(parents=True, exist_ok=True)
    (out / "replay").mkdir(parents=True, exist_ok=True)
    units.to_parquet(out / "units.parquet")
    scores.to_parquet(out / "scores.parquet")
    risk.to_parquet(out / "risk.parquet")
    cells.to_parquet(out / "rain_cells.parquet")
    nodes.to_parquet(out / "graph_nodes.parquet")
    edges.to_parquet(out / "graph_edges.parquet")
    edge_units.to_parquet(out / "edge_units.parquet")
    replay.to_parquet(out / "replay" / f"{REPLAY_DATE}.parquet")
    index = [{"id": REPLAY_DATE, "label": "Ngày phát lại mẫu", "kind": "recorded-day", "time": REPLAY_DATE, "recorded_count": 2}]
    (out / "replay" / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    (out / "model" / "trigger.json").write_text(json.dumps(TRIGGER), encoding="utf-8")
    (Path(root) / "processed" / "model_choice.json").write_text(
        json.dumps({"rain": "none", "tide": "none", "validated": [city]}), encoding="utf-8"
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # đầu ra tiếng Việt khi chuyển hướng trên Windows
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/sample")
    make_sample(target)
    print(f"Đã ghi dữ liệu mẫu vào {target}")
