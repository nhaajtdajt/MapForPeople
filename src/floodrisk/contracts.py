from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Col:
    kind: str  # "str" | "int" | "float" | "bool" | "datetime"
    nullable: bool = False


PRECISIONS = {"high", "medium", "low", "area"}
CAUSES = {"rain", "tide", "combined", "unknown"}
BASES = {"history", "model", "none"}

UNITS = {
    "unit_id": Col("str"), "parent_id": Col("str"), "city": Col("str"), "name": Col("str"),
    "road_class": Col("str"), "road_rank": Col("int"), "length_m": Col("float"),
    "is_bridge": Col("bool"), "is_tunnel": Col("bool"), "rain_cell": Col("int"),
    "elev_min": Col("float", True), "elev_mean": Col("float", True),
    "tpi_300": Col("float", True), "tpi_1000": Col("float", True),
    "dist_water_m": Col("float", True), "built_frac_200": Col("float", True),
}

OBSERVATIONS = {
    "obs_id": Col("str"), "city": Col("str"), "source": Col("str"), "provenance": Col("int"),
    "date": Col("datetime", True), "year": Col("float", True), "hour": Col("float", True),
    "lon": Col("float"), "lat": Col("float"), "loc_precision": Col("str"), "flooded": Col("bool"),
    "depth_cm": Col("float", True), "depth_class": Col("float", True), "cause": Col("str"),
    "street_name": Col("str", True), "unit_id": Col("str", True), "evidence_url": Col("str", True),
}

OBS_UNITS = {"obs_id": Col("str"), "unit_id": Col("str"), "exact": Col("bool"), "spread_m": Col("float")}

GRAPH_NODES = {"node_id": Col("int"), "lon": Col("float"), "lat": Col("float")}
GRAPH_EDGES = {"edge_id": Col("int"), "u": Col("int"), "v": Col("int"), "length_m": Col("float"), "highway": Col("str")}
EDGE_UNITS = {"edge_id": Col("int"), "unit_id": Col("str"), "length_m": Col("float")}

SCORES = {
    "unit_id": Col("str"), "s_rain": Col("float"), "s_tide": Col("float"), "basis": Col("str"),
    "exact": Col("bool"), "loc_weight": Col("float"), "history": Col("int"),
    "max_depth_cm": Col("float", True), "last_year": Col("float", True),
}

# RISK: bảng do score_units trả về. RISK_FILE: risk.parquet trên đĩa. REPLAY: một kịch bản trong replay/.
RISK = {"unit_id": Col("str"), "hour_offset": Col("int"), "risk": Col("float"), "level": Col("int"),
        "t_rain": Col("float"), "t_tide": Col("float")}
RISK_FILE = {**RISK, "computed_at": Col("datetime")}
REPLAY = {**RISK_FILE, "recorded": Col("bool"), "reporters": Col("int"), "reported_level": Col("float", True)}
RAIN_CELLS = {"city": Col("str"), "cell_id": Col("int"), "lon": Col("float"), "lat": Col("float")}
RAIN_HOURLY = {"cell_id": Col("int"), "time": Col("datetime"), "precip_mm": Col("float", True)}
RAIN_DAILY = {"cell_id": Col("int"), "date": Col("datetime"), "r3max": Col("float"), "r24": Col("float")}
TIDE_DAILY = {"date": Col("datetime"), "tide_max": Col("float")}


def _kind_ok(s: pd.Series, kind: str) -> bool:
    t = pd.api.types
    if kind == "str":
        return t.is_string_dtype(s) or t.is_object_dtype(s)
    if kind == "int":
        return t.is_integer_dtype(s)
    if kind == "float":
        return t.is_float_dtype(s) or t.is_integer_dtype(s)
    if kind == "bool":
        return t.is_bool_dtype(s)
    if kind == "datetime":
        return t.is_datetime64_any_dtype(s)
    raise ValueError(f"Kiểu không hỗ trợ: {kind}")


def validate(df: pd.DataFrame, spec: dict[str, Col], name: str) -> None:
    missing = [c for c in spec if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: thiếu cột {missing}")
    for column, col in spec.items():
        s = df[column]
        if not col.nullable and s.isna().any():
            raise ValueError(f"{name}: cột {column} có giá trị rỗng")
        if s.notna().any() and not _kind_ok(s, col.kind):
            raise ValueError(f"{name}: cột {column} phải có kiểu {col.kind}, đang là {s.dtype}")


def validate_units(gdf) -> None:
    validate(gdf, UNITS, "units")
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        raise ValueError("units: hệ tọa độ phải là EPSG:4326")
