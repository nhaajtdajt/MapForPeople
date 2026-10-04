# Nền tảng chung Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng khung repo, cấu hình, bộ kiểm tra định dạng bảng và dữ liệu mẫu, rồi chạy thử các thư viện trên dữ liệu thật, để ba người làm song song từ ngày 2.

**Architecture:** Một gói Python `floodrisk` theo bố cục `src/`. `config.py` giữ danh sách thành phố, các ngưỡng và mọi đường dẫn file; `contracts.py` kiểm tra định dạng các bảng trao đổi giữa ba người; `samples.py` sinh một bộ dữ liệu giả nhỏ đúng định dạng để phần web chạy được khi chưa có dữ liệu thật.

**Tech Stack:** Python 3.12, pandas, GeoPandas, pytest.

**Spec:** `docs/superpowers/plans/2026-10-04-00-quyet-dinh-ky-thuat.md` (bản 3) là tài liệu ràng buộc; `docs/superpowers/specs/2026-10-04-du-bao-nguy-co-ngap-duong-design.md` là bối cảnh.

**Người làm:** kỹ sư phần mềm làm Task 1–3 (đổi từ người AI, theo QĐKT mục 18.3 điểm 13); người AI chạy lại Task 4 khi cần. Task 1–3 phải xong trước trưa ngày 1, vì người dữ liệu và kỹ sư phần mềm cần chúng để bắt đầu việc của mình ngay trong ngày 1. Hai người còn lại đọc và xác nhận `config.py`, `contracts.py`, vì đây là hợp đồng đã đóng băng.

**Trạng thái:** kế hoạch này đã được viết lại theo bản 3 của tài liệu quyết định kỹ thuật, và **đã được chạy thử ngày 04/10/2026**: mã của cả bốn task được chép nguyên văn ra một thư mục tạm, cài bằng đúng `requirements.txt` dưới đây trên Python 3.12, và cả 12 kiểm thử đều đạt; lệnh tạo dữ liệu mẫu và lệnh `smoke` chạy được.

## Global Constraints

- Python 3.12; chạy mọi lệnh từ thư mục gốc của repo.
- Lệnh phải chạy được trên Windows: dùng `python -m ...` và `pytest`, không dùng script bash.
- Tọa độ lưu ở EPSG:4326, thứ tự (kinh độ, vĩ độ).
- Thời gian trong các bảng là giờ Việt Nam, không kèm múi giờ.
- Thư mục `data/` và file `.env` không được commit.
- Kiểm thử không được gọi mạng.
- Tên cột, tên file và giá trị quy ước lấy đúng theo mục 5 của tài liệu quyết định kỹ thuật.
- Hai ngưỡng mức nguy cơ là hằng số: 0,35 và 0,60.

## Review Focus

1. **Thành phố không có trong cấu hình:** gọi hàm đường dẫn với mã thành phố lạ phải báo lỗi rõ ràng, không lặng lẽ tạo thư mục mới.
2. **Bảng thiếu cột:** bộ kiểm tra phải nêu tên các cột thiếu trong thông báo lỗi.
3. **Giá trị rỗng ở cột bắt buộc:** phải bị từ chối, vì phần web sẽ hỏng khi gặp `unit_id` rỗng.
4. **Cột số nguyên bị đọc thành số thực:** `level` hoặc `hour_offset` kiểu số thực phải bị từ chối.
5. **Bảng đoạn chưa có địa hình:** các cột đặc điểm địa hình rỗng toàn bộ vẫn phải được chấp nhận, vì mốc ngày 3 chạy khi chưa có địa hình.

## File Structure

| File | Trách nhiệm |
|---|---|
| `requirements.txt`, `pyproject.toml`, `.gitignore`, `.env.example` | Môi trường |
| `src/floodrisk/config.py` | Thành phố, hằng số, ngưỡng, đường dẫn |
| `src/floodrisk/contracts.py` | Định dạng các bảng và hàm kiểm tra |
| `src/floodrisk/samples.py` | Sinh dữ liệu mẫu |
| `src/floodrisk/smoke.py` | Chạy thử thư viện trên dữ liệu thật |
| `tests/test_config.py`, `tests/test_contracts.py`, `tests/test_samples.py` | Kiểm thử |

---

### Task 1: Khung repo và cấu hình

**Files:**
- Create: `.gitignore`, `requirements.txt`, `pyproject.toml`, `.env.example`
- Create: `src/floodrisk/__init__.py`, `src/floodrisk/config.py`
- Create: `src/floodrisk/data/__init__.py`, `src/floodrisk/model/__init__.py`, `src/floodrisk/api/__init__.py`, `src/floodrisk/jobs/__init__.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: không có.
- Produces: `City`, `CITIES`, `RAIN_HISTORY_START`, `CUTOFF`, `GRID_CELL_M`, `PARENT_CELL_M`, `RAIN_CELL_DEG`, `LEVEL_MEDIUM`, `LEVEL_HIGH`, `TZ`, `data_dir()`, `processed_dir(city)`, `live_dir()`, và các hàm đường dẫn `units_path`, `observations_path`, `obs_units_path`, `rain_cells_path`, `rain_daily_path`, `scores_path`, `risk_path`, `trigger_path`, `replay_dir`, `graph_nodes_path`, `graph_edges_path`, `edge_units_path`, `inputs_dir` (nhận `city`), `model_choice_path`, `tide_coef_path`, `tide_daily_path` (không tham số).

- [ ] **Step 1: Tạo repo và môi trường**

Môi trường ảo phải được tạo bằng **CPython 3.12**. Trước tiên chạy `python --version` trong đúng cửa sổ dòng lệnh sẽ dùng. Trên máy đã chạy thử ngày 04/10, lệnh `python` trong Git Bash trỏ tới bản Python của MSYS2 (không cài được GeoPandas), còn bản mặc định của Windows là 3.14. Vì vậy gọi thẳng trình thông dịch 3.12:

```bash
git init
"C:\Users\NHAT DAT\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
```

Trên máy khác, thay đường dẫn bằng nơi cài Python 3.12 của máy đó. Kích hoạt môi trường: trên Windows chạy `.venv\Scripts\activate`, trên macOS hoặc Linux chạy `source .venv/bin/activate`. Sau khi kích hoạt, `python --version` phải in ra `Python 3.12.x`.

- [ ] **Step 2: Viết các file môi trường**

File `.env` (chứa hai khóa Goong thật của nhóm) và `.gitignore` đã có sẵn ở thư mục gốc từ ngày 04/10. Không ghi đè `.env`, và kiểm tra `.gitignore` có dòng `.env` trước lần commit đầu tiên.

`.gitignore`:

```
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
.env
data/
web/node_modules/
web/dist/
```

`requirements.txt`:

```
numpy==2.5.3
pandas==3.0.6
pyarrow==25.0.1
geopandas==1.2.0
shapely==2.1.2
pyproj==3.8.0
pyogrio==0.13.0
rasterio==1.5.2
scipy==1.18.1
osmnx==2.1.1
scikit-learn==1.9.1
lightgbm==4.7.0
utide==0.4.0
joblib==1.6.0
tabulate==0.10.0
requests==2.34.2
httpx==0.28.1
fastapi==0.142.2
uvicorn[standard]==0.54.0
pydantic==2.13.5
pytest==9.1.1
```

Các phiên bản này được ghim đúng theo bộ đã cài và chạy thử thành công ngày 04/10/2026 trên Windows với Python 3.12. Ghim cứng để ba người có cùng một môi trường.

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "floodrisk"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.env.example`:

```
GOONG_API_KEY=
VITE_GOONG_MAP_KEY=
VITE_API_BASE=
FLOODRISK_DATA=data
REFRESH_MINUTES=60
FLOODRISK_CONTACT=
FLOODRISK_TEST_TOOLS=
```

Tạo năm file `__init__.py` rỗng ở các đường dẫn đã liệt kê.

- [ ] **Step 3: Cài đặt**

```bash
pip install -r requirements.txt
pip install -e .
```

Expected: kết thúc bằng `Successfully installed floodrisk-0.1.0`.

- [ ] **Step 4: Viết kiểm thử thất bại**

`tests/test_config.py`:

```python
import pytest

from floodrisk import config


def test_cities_have_valid_bbox_and_center():
    assert set(config.CITIES) == {"hcm", "danang"}
    for city in config.CITIES.values():
        west, south, east, north = city.bbox
        assert west < east and south < north
        lon, lat = city.center
        assert west < lon < east and south < lat < north


def test_grid_cells_nest_and_levels_are_ordered():
    assert config.PARENT_CELL_M % config.GRID_CELL_M == 0
    assert 0 < config.LEVEL_MEDIUM < config.LEVEL_HIGH < 1


def test_data_dir_follows_env(monkeypatch, tmp_path):
    monkeypatch.setenv("FLOODRISK_DATA", str(tmp_path))
    assert config.data_dir() == tmp_path
    assert config.units_path("hcm") == tmp_path / "processed" / "hcm" / "units.parquet"
    assert config.obs_units_path("hcm") == tmp_path / "processed" / "hcm" / "obs_units.parquet"
    assert config.trigger_path("hcm") == tmp_path / "processed" / "hcm" / "model" / "trigger.json"
    assert config.replay_dir("hcm") == tmp_path / "processed" / "hcm" / "replay"
    assert config.graph_nodes_path("hcm") == tmp_path / "processed" / "hcm" / "graph_nodes.parquet"
    assert config.graph_edges_path("hcm") == tmp_path / "processed" / "hcm" / "graph_edges.parquet"
    assert config.edge_units_path("hcm") == tmp_path / "processed" / "hcm" / "edge_units.parquet"
    assert config.inputs_dir("hcm") == tmp_path / "raw" / "inputs" / "hcm"
    assert config.model_choice_path() == tmp_path / "processed" / "model_choice.json"
    assert config.live_dir() == tmp_path / "raw" / "live"


def test_unknown_city_raises():  # Review Focus 1
    with pytest.raises(KeyError, match="hanoi"):
        config.processed_dir("hanoi")
```

- [ ] **Step 5: Chạy để thấy thất bại**

Run: `pytest tests/test_config.py -v`
Expected: FAIL với `AttributeError: module 'floodrisk.config' has no attribute 'CITIES'`

- [ ] **Step 6: Viết `config.py`**

```python
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


def data_dir() -> Path:
    return Path(os.environ.get("FLOODRISK_DATA", "data"))


def live_dir() -> Path:
    return data_dir() / "raw" / "live"


def processed_dir(city: str) -> Path:
    if city not in CITIES:
        raise KeyError(f"Thành phố chưa có trong cấu hình: {city}")
    return data_dir() / "processed" / city


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
```

- [ ] **Step 7: Chạy để thấy đạt**

Run: `pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 8: Commit**

```bash
git add .gitignore requirements.txt pyproject.toml .env.example src tests
git commit -m "chore: scaffold floodrisk package and city config"
```

---

### Task 2: Hợp đồng dữ liệu

**Files:**
- Create: `src/floodrisk/contracts.py`
- Test: `tests/test_contracts.py`

**Interfaces:**
- Consumes: không có.
- Produces: `Col`; các bảng định dạng `UNITS`, `OBSERVATIONS`, `OBS_UNITS`, `GRAPH_NODES`, `GRAPH_EDGES`, `EDGE_UNITS`, `SCORES`, `RISK`, `RISK_FILE`, `REPLAY`, `RAIN_CELLS`, `RAIN_HOURLY`, `RAIN_DAILY`, `TIDE_DAILY`; các tập giá trị `PRECISIONS`, `CAUSES`, `BASES`; `validate(df, spec, name) -> None`; `validate_units(gdf) -> None`.

- [ ] **Step 1: Viết kiểm thử thất bại**

`tests/test_contracts.py`:

```python
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from floodrisk import contracts


def _risk():
    return pd.DataFrame({"unit_id": ["a", "b"], "hour_offset": [0, 0], "risk": [0.1, 0.9], "level": [0, 2],
                         "t_rain": [0.2, 0.9], "t_tide": [0.0, 0.0]})


def test_valid_table_passes():
    contracts.validate(_risk(), contracts.RISK, "risk")


def test_missing_column_names_the_column():  # Review Focus 2
    with pytest.raises(ValueError, match="level"):
        contracts.validate(_risk().drop(columns="level"), contracts.RISK, "risk")


def test_null_in_required_column_rejected():  # Review Focus 3
    df = _risk()
    df.loc[0, "unit_id"] = None
    with pytest.raises(ValueError, match="unit_id"):
        contracts.validate(df, contracts.RISK, "risk")


def test_float_in_integer_column_rejected():  # Review Focus 4
    df = _risk()
    df["level"] = df["level"].astype(float)
    with pytest.raises(ValueError, match="level"):
        contracts.validate(df, contracts.RISK, "risk")


def test_scores_and_obs_units_pass():
    scores = pd.DataFrame({
        "unit_id": ["a", "b"], "s_rain": [0.95, 0.0], "s_tide": [0.0, 0.5], "basis": ["history", "model"],
        "exact": [True, False], "loc_weight": [1.0, 0.25], "history": [3, 0],
        "max_depth_cm": [40.0, None], "last_year": [2024.0, None],
    })
    contracts.validate(scores, contracts.SCORES, "scores")
    assert set(scores["basis"]) <= contracts.BASES
    obs_units = pd.DataFrame({"obs_id": ["o1"], "unit_id": ["a"], "exact": [True], "spread_m": [180.0]})
    contracts.validate(obs_units, contracts.OBS_UNITS, "obs_units")


def _units(crs, with_terrain=True):
    value = 1.0 if with_terrain else None
    gdf = gpd.GeoDataFrame(
        {
            "unit_id": ["hcm-1"], "parent_id": ["hcm-p-1"], "city": ["hcm"], "name": ["Đường A"],
            "road_class": ["residential"], "road_rank": [1], "length_m": [100.0],
            "is_bridge": [False], "is_tunnel": [False], "rain_cell": [0],
            "elev_min": [value], "elev_mean": [value], "tpi_300": [value], "tpi_1000": [value],
            "dist_water_m": [value], "built_frac_200": [value],
        },
        geometry=[LineString([(106.7, 10.78), (106.701, 10.78)])],
        crs=crs,
    )
    features = ["elev_min", "elev_mean", "tpi_300", "tpi_1000", "dist_water_m", "built_frac_200"]
    return gdf.astype({c: "float64" for c in features})


def test_units_pass_with_and_without_terrain():  # Review Focus 5
    contracts.validate_units(_units(4326))
    contracts.validate_units(_units(4326, with_terrain=False))


def test_units_reject_wrong_crs():
    with pytest.raises(ValueError, match="4326"):
        contracts.validate_units(_units(32648))
```

- [ ] **Step 2: Chạy để thấy thất bại**

Run: `pytest tests/test_contracts.py -v`
Expected: FAIL với `AttributeError: module 'floodrisk.contracts' has no attribute 'RISK'`

- [ ] **Step 3: Viết `contracts.py`**

```python
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
```

- [ ] **Step 4: Chạy để thấy đạt**

Run: `pytest tests/test_contracts.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/floodrisk/contracts.py tests/test_contracts.py
git commit -m "feat: add table contracts shared by data, model and web"
```

---

### Task 3: Dữ liệu mẫu

**Files:**
- Create: `src/floodrisk/samples.py`
- Test: `tests/test_samples.py`

**Interfaces:**
- Consumes: `config.CITIES`, `LEVEL_MEDIUM`, `LEVEL_HIGH`, `contracts`.
- Produces: `make_sample(root: Path, city: str = "hcm", n: int = 4, seed: int = 0) -> None`. Ghi dưới `root/processed/`: `{city}/units.parquet`, `{city}/scores.parquet`, `{city}/risk.parquet`, `{city}/rain_cells.parquet`, `{city}/graph_nodes.parquet`, `{city}/graph_edges.parquet`, `{city}/edge_units.parquet`, `{city}/model/trigger.json`, `{city}/replay/2024-10-18.parquet`, `{city}/replay/index.json`, `model_choice.json`. Lệnh: `python -m floodrisk.samples data/sample`.

Mạng đường mẫu là lưới 4 × 4 giao lộ, mỗi khúc 200 m. Kỹ sư phần mềm dùng nó để viết và kiểm thử thuật toán tìm đường khi chưa có mạng đường thật.

Tám tuyến mẫu được đánh số `hcm-sample00` tới `hcm-sample07` theo thứ tự: Ngang 1, Dọc 1, Ngang 2, Dọc 2, Ngang 3, Dọc 3, Ngang 4, Dọc 4. Kiểm thử của kế hoạch 04 dựa vào thứ tự này.

- [ ] **Step 1: Viết kiểm thử thất bại**

`tests/test_samples.py`:

```python
import json

import geopandas as gpd
import pandas as pd

from floodrisk import config, contracts
from floodrisk.samples import make_sample


def test_sample_matches_contracts(monkeypatch, tmp_path):
    monkeypatch.setenv("FLOODRISK_DATA", str(tmp_path))
    make_sample(tmp_path)

    units = gpd.read_parquet(config.units_path("hcm"))
    contracts.validate_units(units)
    assert len(units) == 8 and units["unit_id"].iloc[6] == "hcm-sample06"

    scores = pd.read_parquet(config.scores_path("hcm"))
    contracts.validate(scores, contracts.SCORES, "scores")
    assert set(scores["basis"]) <= contracts.BASES and {"history", "model"} <= set(scores["basis"])
    assert scores["loc_weight"].between(0, 1).all()

    risk = pd.read_parquet(config.risk_path("hcm"))
    contracts.validate(risk, contracts.RISK_FILE, "risk")
    assert sorted(risk["hour_offset"].unique()) == [0, 1, 2]
    assert len(risk) == 3 * len(units)
    now = risk[risk["hour_offset"] == 0]
    assert (now["level"] == 2).sum() == 3 and (now["level"] == 1).sum() == 2

    cells = pd.read_parquet(config.rain_cells_path("hcm"))
    contracts.validate(cells, contracts.RAIN_CELLS, "rain_cells")

    nodes = pd.read_parquet(config.graph_nodes_path("hcm"))
    edges = gpd.read_parquet(config.graph_edges_path("hcm"))
    edge_units = pd.read_parquet(config.edge_units_path("hcm"))
    contracts.validate(nodes, contracts.GRAPH_NODES, "graph_nodes")
    contracts.validate(edges, contracts.GRAPH_EDGES, "graph_edges")
    contracts.validate(edge_units, contracts.EDGE_UNITS, "edge_units")
    assert len(nodes) == 16 and len(edges) == 48 and len(edge_units) == 48
    assert set(edge_units["unit_id"]) == set(units["unit_id"])

    trigger = json.loads(config.trigger_path("hcm").read_text(encoding="utf-8"))
    assert len(trigger["rain"]["coef"]) == 2 and trigger["rain"]["cuts"]["medium"] < trigger["rain"]["cuts"]["high"]

    choice = json.loads(config.model_choice_path().read_text(encoding="utf-8"))
    assert choice["validated"] == ["hcm"]

    index = json.loads((config.replay_dir("hcm") / "index.json").read_text(encoding="utf-8"))
    assert index[0]["id"] == "2024-10-18" and index[0]["kind"] == "recorded-day" and index[0]["recorded_count"] == 2
    replay = pd.read_parquet(config.replay_dir("hcm") / "2024-10-18.parquet")
    contracts.validate(replay, contracts.REPLAY, "replay")
    assert replay["recorded"].sum() == 2 * 3 and (replay["reporters"] == 0).all()
```

- [ ] **Step 2: Chạy để thấy thất bại**

Run: `pytest tests/test_samples.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'floodrisk.samples'`

- [ ] **Step 3: Viết `samples.py`**

```python
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
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/sample")
    make_sample(target)
    print(f"Đã ghi dữ liệu mẫu vào {target}")
```

- [ ] **Step 4: Chạy để thấy đạt**

Run: `pytest tests/test_samples.py -v`
Expected: 1 passed

- [ ] **Step 5: Sinh dữ liệu mẫu để phần web dùng**

Run: `python -m floodrisk.samples data/sample`
Expected: thư mục `data/sample/processed/hcm/` có 7 file `.parquet`, một thư mục `replay` và một thư mục `model`.

- [ ] **Step 6: Chạy toàn bộ kiểm thử**

Run: `pytest -v`
Expected: 12 passed

- [ ] **Step 7: Commit và đẩy lên**

```bash
git add src/floodrisk/samples.py tests/test_samples.py
git commit -m "feat: add sample data generator for web development"
git branch -M main
```

Sau đó tạo repo trên GitHub của nhóm, thêm remote, đẩy `main`, và mỗi người tạo nhánh của mình (`data`, `model`, `web`).

---

### Task 4: Chạy thử thư viện trên dữ liệu thật

Mã trong các kế hoạch 02–04 chưa từng được chạy. Task này làm lộ lỗi thư viện ngay trong ngày 1, trước khi ba người chia nhánh.

**Files:**
- Create: `src/floodrisk/smoke.py`

**Interfaces:**
- Consumes: `config.CITIES`.
- Produces: lệnh `python -m floodrisk.smoke`, in ra phiên bản thư viện và kết quả từng bước.

- [ ] **Step 1: Viết `smoke.py`**

```python
from __future__ import annotations

from importlib.metadata import version

from floodrisk.config import CITIES

PACKAGES = ["numpy", "pandas", "geopandas", "shapely", "pyogrio", "rasterio", "osmnx", "scikit-learn", "lightgbm", "utide", "fastapi"]


def main() -> None:
    for name in PACKAGES:
        print(f"{name:14s} {version(name)}")

    import osmnx as ox

    lon, lat = CITIES["hcm"].center
    bbox = (lon - 0.005, lat - 0.005, lon + 0.005, lat + 0.005)  # khoảng 1 km quanh trung tâm
    graph = ox.graph_from_bbox(bbox, network_type="drive", simplify=True)
    edges = ox.graph_to_gdfs(graph, nodes=False).reset_index()
    print("Số cạnh OpenStreetMap:", len(edges))
    print("Các cột:", sorted(edges.columns))
    for column in ("name", "highway", "bridge", "tunnel"):
        print(f"  có cột {column}: {column in edges.columns}")
    projected = edges.to_crs(edges.estimate_utm_crs())
    print("Hệ tọa độ mét:", projected.crs.to_epsg(), "| cạnh dài nhất (m):", round(float(projected.length.max()), 1))

    import numpy as np
    import pandas as pd
    from utide import reconstruct, solve

    times = pd.date_range("2024-01-01", periods=24 * 60, freq="h")
    days = (times.to_numpy() - np.datetime64("1970-01-01")) / np.timedelta64(1, "D")
    height = np.cos(2 * np.pi * np.arange(len(times)) / 12.4206)
    coef = solve(days, height, lat=10.34, epoch="1970-01-01", method="ols", conf_int="none", trend=False, verbose=False)
    back = reconstruct(days[:24], coef, epoch="1970-01-01", verbose=False)
    print("utide: sai số lớn nhất (m):", round(float(np.max(np.abs(back.h - height[:24]))), 3))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Chạy**

Run: `python -m floodrisk.smoke`

Expected:
- Mười một dòng phiên bản thư viện.
- Số cạnh lớn hơn 50; có cột `name` và `highway`.
- Sai số utide dưới 0,05.

Ghi lại vào nhật ký nhóm ba điều: cột `bridge` và `tunnel` có mặt hay không (kế hoạch 02 Task 5 cần chúng; nếu thiếu thì coi mọi cạnh là không phải cầu); phiên bản OSMnx; và mọi lỗi gặp phải. Nếu một lời gọi thư viện báo sai tham số, sửa ngay ở đây và báo cho người sẽ dùng thư viện đó.

- [ ] **Step 3: Đọc thử bộ IRD**

Chép `HCMC_Floods_BDD.gpkg` từ `D:\HK1 4 year\Hackathon\mlai-car-access\data\flood\ird-hcmc\` vào `data/raw/ird/`, rồi:

```bash
python -c "import geopandas as gpd; g = gpd.read_file('data/raw/ird/HCMC_Floods_BDD.gpkg'); print(len(g), g.crs, sorted(g.columns))"
```

Expected: `425`, một hệ tọa độ không rỗng, và danh sách cột có `Location_name`, `Spatial_precision`, `Geocoding_method`, `Water_height_max_cm`. Gửi danh sách cột này cho người dữ liệu.

- [ ] **Step 4: Commit**

```bash
git add src/floodrisk/smoke.py
git commit -m "chore: add library smoke run on real data"
```
