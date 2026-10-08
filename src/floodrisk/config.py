from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class City:
    key: str
    name: str
    bbox: tuple[float, float, float, float]  # west, south, east, north
    center: tuple[float, float]  # lon, lat
    has_tide: bool


CITIES: dict[str, City] = {
    "hcm": City("hcm", "TP. Hồ Chí Minh", (106.55, 10.62, 106.90, 10.95), (106.70, 10.78), True),
    "danang": City("danang", "Đà Nẵng", (108.05, 15.95, 108.35, 16.17), (108.21, 16.06), False),
}

RAIN_HISTORY_START = "2016-01-01"
CUTOFF = "2025-01-01"  # mọi phép kiểm chứng chỉ học từ dữ liệu trước ngày này
GRID_CELL_M = 200  # ô lưới của đoạn
PARENT_CELL_M = 1000  # ô lưới của tuyến
RAIN_CELL_DEG = 0.1
LEVEL_MEDIUM = 0.35
LEVEL_HIGH = 0.60
TZ = "Asia/Ho_Chi_Minh"
MODEL_VERSION = "final_2025-01-01"  # thư mục mô hình đã chốt trong repo flood_prediction_models
MODEL_CITY = {"hcm": "ho_chi_minh", "danang": "da_nang"}  # tên thành phố trong repo mô hình


def data_dir() -> Path:
    return Path(os.environ.get("FLOODRISK_DATA", "data"))


def live_dir() -> Path:
    return data_dir() / "raw" / "live"


def processed_dir(city: str) -> Path:
    if city not in CITIES:
        raise KeyError(f"Thành phố chưa có trong cấu hình: {city}")
    return data_dir() / "processed" / city


def model_dir() -> Path:
    """Các file mô hình chép nguyên văn từ repo flood_prediction_models (ghi chú 11, QĐ1)."""
    return data_dir() / "model"


def route_table_path(city: str) -> Path:
    return processed_dir(city) / "route_table.parquet"


def risk_layer_path(city: str) -> Path:
    return processed_dir(city) / "risk_routes.geojson.gz"


def tide_hourly_path(city: str) -> Path:
    return processed_dir(city) / "tide_hourly.parquet"


def flood_points_path(city: str) -> Path:
    """Danh sách điểm ngập Phòng CSGT công bố ngày 06/10/2026, đã định vị (tools/doi_chieu_122_diem.py)."""
    return processed_dir(city) / "diem_ngap_pc08_2026-10-06.csv"


def units_path(city: str) -> Path:
    return processed_dir(city) / "units.parquet"


def observations_path(city: str) -> Path:
    return processed_dir(city) / "observations.parquet"


def obs_units_path(city: str) -> Path:
    return processed_dir(city) / "obs_units.parquet"


def rain_cells_path(city: str) -> Path:
    return processed_dir(city) / "rain_cells.parquet"


def rain_daily_path(city: str) -> Path:
    return processed_dir(city) / "rain_daily.parquet"


def scores_path(city: str) -> Path:
    return processed_dir(city) / "scores.parquet"


def risk_path(city: str) -> Path:
    return processed_dir(city) / "risk.parquet"


def trigger_path(city: str) -> Path:
    return processed_dir(city) / "model" / "trigger.json"


def replay_dir(city: str) -> Path:
    return processed_dir(city) / "replay"


def graph_nodes_path(city: str) -> Path:
    return processed_dir(city) / "graph_nodes.parquet"


def graph_edges_path(city: str) -> Path:
    return processed_dir(city) / "graph_edges.parquet"


def edge_units_path(city: str) -> Path:
    return processed_dir(city) / "edge_units.parquet"


def inputs_dir(city: str) -> Path:
    if city not in CITIES:
        raise KeyError(f"Thành phố chưa có trong cấu hình: {city}")
    return data_dir() / "raw" / "inputs" / city


def model_choice_path() -> Path:
    return data_dir() / "processed" / "model_choice.json"


def tide_coef_path() -> Path:
    return data_dir() / "processed" / "tide_coef.joblib"


def tide_daily_path() -> Path:
    return data_dir() / "processed" / "tide_daily.parquet"
