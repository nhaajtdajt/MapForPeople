"""Dựng các file máy chủ cần từ mô hình của repo flood_prediction_models (ghi chú 11, QĐ1 tới QĐ3).

    python tools/dung_lop_mo_hinh.py --city hcm [--routes <bảng tuyến>]

Cần repo flood_prediction_models nằm cạnh repo này.

1. Chép nguyên văn các file mô hình dùng lúc chạy vào data/model/ và ghi commit gốc vào SOURCE.json.
2. Ghép hình học tuyến với bảng điểm theo thứ tự dòng. Trước khi ghép, kiểm rằng hai bảng dài bằng nhau,
   tuyến có tên trùng mã ở đúng dòng và cờ in_universe trùng ở mọi dòng. Mã tuyến không tên phụ thuộc
   máy dựng, nên luôn lấy mã từ bảng điểm. Bảng tuyến mặc định là
   data/raw/model_build/<tên thành phố>_routes_linux.parquet (kết quả build_routes.py của repo mô hình, chạy trên Linux).
3. Xếp nhóm tuyến như run_hourly.py rồi ghi vào data/processed/<thành phố>/:
   - route_table.parquet     mọi tuyến: mã, tên, loại đường, chiều dài, nhóm theo mưa và triều, lịch sử ngập;
   - risk_routes.geojson.gz  hình học các tuyến thuộc nhóm A hoặc B, cho lớp bản đồ;
   - tide_hourly.parquet     mực triều thiên văn Vũng Tàu từng giờ (chỉ thành phố có mô hình triều).

Chạy lại mỗi khi bạn làm mô hình train lại.
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from floodrisk import config
from floodrisk.model.levels import live_bands

ROOT = Path(__file__).resolve().parents[1]
MODEL_REPO = ROOT.parent / "flood_prediction_models"
UTM = {"hcm": 32648, "danang": 32649}
SIMPLIFY_M = 3.0
TIDE_FROM = "2026-10-01"
COMMON_FILES = ["final_config.json", "combination_thresholds.json", f"{config.MODEL_VERSION}/rain_trigger.json"]
CITY_FILES = ["m2_{slug}_tide.json", f"{config.MODEL_VERSION}/cdfs/{{slug}}_ifs_reference.parquet",
              f"{config.MODEL_VERSION}/cdfs/{{slug}}_era5_reference.parquet",
              f"{config.MODEL_VERSION}/{{slug}}/route_susceptibility.parquet"]


def copy_model(slug: str) -> list[str]:
    target = config.model_dir()
    files = COMMON_FILES + [f.format(slug=slug) for f in CITY_FILES]
    for name in files:
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(MODEL_REPO / "models" / name, target / name)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=MODEL_REPO, capture_output=True, text=True, check=True).stdout.strip()
    source_file = target / "SOURCE.json"
    source = json.loads(source_file.read_text(encoding="utf-8")) if source_file.exists() else {"repo": "flood_prediction_models", "cities": {}}
    source["cities"][slug] = {"commit": commit, "files": files,
                              "copied_at": datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")}
    source_file.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return files


def aligned_routes(routes_file: Path, scores: pd.DataFrame) -> gpd.GeoDataFrame:
    routes = gpd.read_parquet(routes_file)
    if len(routes) != len(scores):
        sys.exit(f"Bảng tuyến có {len(routes)} dòng, bảng điểm có {len(scores)} dòng: không cùng một lần dựng.")
    named = routes.named.to_numpy(bool)
    same_id = routes.route_id.to_numpy() == scores.route_id.to_numpy()
    same_universe = routes.in_universe.to_numpy(bool) == (scores.in_universe.to_numpy() == 1)
    if not same_id[named].all() or not same_universe.all():
        sys.exit(f"Bảng tuyến không khớp bảng điểm theo dòng: tuyến có tên trùng mã {same_id[named].mean():.2%}, "
                 f"cờ in_universe trùng {same_universe.mean():.2%}. Cần bảng tuyến dựng từ đúng bản OpenStreetMap của mô hình.")
    print(f"ghép theo dòng: {len(routes)} tuyến; tuyến có tên trùng mã 100%; tuyến không tên trùng mã {same_id[~named].mean():.1%} "
          f"(lấy mã của bảng điểm); cờ in_universe trùng 100%")
    routes = routes.reset_index(drop=True)
    routes["route_id"] = scores.route_id.to_numpy()
    return routes


def line_coordinates(geom) -> dict | None:
    lines = [g for g in getattr(geom, "geoms", [geom]) if g.geom_type == "LineString" and not g.is_empty]
    parts = [[[round(x, 5), round(y, 5)] for x, y in line.coords] for line in lines]
    parts = [p for p in parts if len(p) >= 2]
    if not parts:
        return None
    return {"type": "LineString", "coordinates": parts[0]} if len(parts) == 1 else {"type": "MultiLineString", "coordinates": parts}


def build(city: str, routes_file: Path) -> None:
    slug = config.MODEL_CITY[city]
    files = copy_model(slug)
    print(f"đã chép {len(files)} file mô hình vào {config.model_dir()}")

    scores = pd.read_parquet(config.model_dir() / config.MODEL_VERSION / slug / "route_susceptibility.parquet")
    routes = aligned_routes(routes_file, scores)
    table = pd.DataFrame({
        "route_id": scores.route_id.to_numpy(), "name": routes.name.to_numpy(), "highway_class": routes.highway_class.to_numpy(),
        "length_m": routes.length_m.to_numpy(float).round(1), "in_universe": scores.in_universe.to_numpy() == 1,
        "band_rain": live_bands(scores.S_hyb_rain.to_numpy()), "band_tide": live_bands(scores.S_hyb_tide.to_numpy()),
        "history_rain": scores.H_rain.to_numpy() > 0, "history_tide": scores.H_tide.to_numpy() > 0,
        "history_dates_rain": scores.n_distinct_dates_rain.to_numpy().astype("int32"),
        "history_dates_tide": scores.n_distinct_dates_tide.to_numpy().astype("int32"),
    })
    out = config.processed_dir(city)
    out.mkdir(parents=True, exist_ok=True)
    table.to_parquet(config.route_table_path(city), index=False, compression="zstd")

    drawn = np.flatnonzero((table.band_rain.to_numpy() > 0) | (table.band_tide.to_numpy() > 0))
    geometry = routes.geometry.iloc[drawn].to_crs(UTM[city]).simplify(SIMPLIFY_M).to_crs(4326)
    features = []
    for row, geom in zip(drawn, geometry.to_numpy()):
        shape = line_coordinates(geom)
        if shape is None:
            continue
        r = table.iloc[row]
        features.append({"type": "Feature", "id": int(row), "geometry": shape, "properties": {
            "id": r.route_id, "name": r["name"] if isinstance(r["name"], str) else "", "cls": r.highway_class,
            "len": int(round(r.length_m)),
            "br": int(r.band_rain), "bt": int(r.band_tide),
            "hr": int(r.history_dates_rain) if r.history_rain else 0, "ht": int(r.history_dates_tide) if r.history_tide else 0}})
    text = json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":"))
    with open(config.risk_layer_path(city), "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as packed:
        packed.write(text.encode("utf-8"))

    tide_file = MODEL_REPO / "data" / "processed" / slug / "drivers_tide_hourly.parquet"
    tide_note = "không có mô hình triều"
    if json.loads((config.model_dir() / f"m2_{slug}_tide.json").read_text(encoding="utf-8"))["kind"] != "zero":
        tide = pd.read_parquet(tide_file, columns=["time_utc", "astro_m"])
        tide["time_utc"] = pd.to_datetime(tide.time_utc, utc=True)
        tide = tide[tide.time_utc >= pd.Timestamp(TIDE_FROM, tz="UTC")].reset_index(drop=True)
        tide.to_parquet(config.tide_hourly_path(city), index=False, compression="zstd")
        tide_note = f"{len(tide)} giờ, tới {tide.time_utc.max():%d/%m/%Y}"

    def count(col: str, band: int) -> int:
        return int((table[col] == band).sum())

    print(f"{city}: {len(table)} tuyến | nhóm theo mưa A {count('band_rain', 2)}, B {count('band_rain', 1)} | theo triều A {count('band_tide', 2)}, "
          f"B {count('band_tide', 1)} | tuyến từng ngập {int((table.history_rain | table.history_tide).sum())}")
    print(f"lớp bản đồ: {len(features)} tuyến, {len(text) / 1e6:.1f} MB, nén còn {config.risk_layer_path(city).stat().st_size / 1e6:.1f} MB | "
          f"bảng tuyến {config.route_table_path(city).stat().st_size / 1e6:.1f} MB | triều: {tide_note}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--city", required=True, choices=sorted(config.MODEL_CITY))
    parser.add_argument("--routes", type=Path)
    args = parser.parse_args()
    default = config.data_dir() / "raw" / "model_build" / f"{config.MODEL_CITY[args.city]}_routes_linux.parquet"
    build(args.city, args.routes or default)
