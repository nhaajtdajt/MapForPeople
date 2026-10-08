"""Mức mưa và mức triều của ngày (Mô hình 2), đúng như tác vụ mỗi giờ của repo mô hình.

Chép từ flood_prediction_models, commit 842da0a:
- `rain_windows`, `rain_trigger`, `fetch_rain`: `scripts/run_hourly.py` (`run`, `_trigger_rain`, `_live_weather`);
- `tide_trigger`: nhánh `percentile` và `zero` của `_apply` trong `src/floodrisk/trigger.py`;
- `GRIDS`: vùng làm việc trong `src/floodrisk/cities.py` và lưới điểm trong `run_hourly.grid`.

Không sửa phép tính ở đây. Mô hình đổi thì chép lại từ repo gốc (ghi chú 11, QĐ1).
"""
from __future__ import annotations

import math

import httpx
import numpy as np
import pandas as pd
from scipy.special import expit

TZ = "Asia/Ho_Chi_Minh"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "floodrisk-hackathon/0.1 (hourly route-risk forecast)"
HORIZONS = (0, 1, 2)  # giờ này, +1 giờ, +2 giờ

# thành phố (tên trong repo mô hình) -> ((tây, nam, đông, bắc), số hàng, số cột) của lưới điểm lấy mưa
GRIDS: dict[str, tuple[tuple[float, float, float, float], int, int]] = {
    "ho_chi_minh": ((106.4363502282, 10.55, 107.0, 11.05), 3, 3),
    "da_nang": ((108.0331223, 15.8181984, 108.35, 16.1601221), 2, 3),
}


class ModelUnavailable(ValueError):
    """Open-Meteo không phục vụ mô hình thời tiết được hỏi (HTTP 400 hoặc 422)."""


def grid_points(city: str) -> list[tuple[float, float]]:
    (w, s, e, n), ny, nx = GRIDS[city]
    return [(float(y), float(x)) for y in np.linspace(s, n, ny) for x in np.linspace(w, e, nx)]


def fetch_rain(city: str, model: str = "ecmwf_ifs", client: httpx.Client | None = None) -> pd.Series:
    """Mưa từng giờ (mm) của 72 giờ qua và 12 giờ tới: giá trị lớn nhất trên các điểm lưới của thành phố."""
    pts = grid_points(city)
    params = {"latitude": ",".join(f"{a:.6f}" for a, _ in pts), "longitude": ",".join(f"{b:.6f}" for _, b in pts),
              "hourly": "precipitation", "past_hours": 72, "forecast_hours": 12, "timezone": TZ}
    if model != "best_match":
        params["models"] = model
    get = client.get if client is not None else httpx.get
    r = get(FORECAST_URL, params=params, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=90)
    if r.status_code in (400, 422):
        raise ModelUnavailable(f"Open-Meteo không có mô hình {model} (HTTP {r.status_code})")
    r.raise_for_status()
    payload = r.json()
    items = payload if isinstance(payload, list) else [payload]
    if len(items) != len(pts):
        raise ValueError(f"Open-Meteo trả {len(items)} điểm, cần {len(pts)}")
    frames = []
    for item in items:
        hourly = item.get("hourly") or {}
        times = pd.to_datetime(hourly.get("time", []))
        values = pd.to_numeric(pd.Series(hourly.get("precipitation", [])), errors="coerce")
        if times.empty or values.isna().all():
            raise ValueError("Open-Meteo trả chuỗi mưa rỗng")
        if times.tz is None:
            times = times.tz_localize(TZ)
        frames.append(pd.Series(values.to_numpy(), index=times))
    return pd.concat(frames, axis=1).max(axis=1).sort_index()


def rain_windows(series: pd.Series, at: pd.Timestamp) -> list[dict]:
    """Hai số đầu vào của mức mưa cho từng giờ dự báo: mưa 3 giờ lớn nhất trong 6 giờ qua, và tổng mưa 24 giờ qua."""
    rows = []
    for h in HORIZONS:
        t = at + pd.Timedelta(hours=h)
        sub = series.loc[(series.index > t - pd.Timedelta(hours=6)) & (series.index <= t)].dropna()
        if len(sub) < 6:
            raise ValueError(f"Thiếu số liệu mưa cho 6 giờ trước {t}")
        total24 = series.loc[(series.index > t - pd.Timedelta(hours=24)) & (series.index <= t)].dropna().sum()
        rows.append({"valid_time": t, "rain_max_3h_mm": float(sub.rolling(3, min_periods=3).sum().max()),
                     "rain_total_mm": float(total24)})
    return rows


def quantile(value: float, reference) -> float:
    """Vị trí của `value` trong các ngày tham chiếu, từ 0 tới 1."""
    x = pd.to_numeric(pd.Series(reference), errors="coerce").dropna().to_numpy(float)
    return float(np.searchsorted(np.sort(x), value, side="right") / max(1, len(x)))


def rain_trigger(rain_max_3h_mm: float, rain_total_mm: float, cfg: dict, reference: pd.DataFrame) -> float:
    """Mức mưa T: hồi quy trên logit của hai vị trí phần trăm. `cfg` là rain_trigger.json, `reference` là bảng cdfs."""
    q = {"rain_max_3h_mm": np.clip(quantile(rain_max_3h_mm, reference.rain_max_3h_mm), .001, .999),
         "rain_total_mm": np.clip(quantile(rain_total_mm, reference.rain_total_mm), .001, .999)}
    z = np.asarray([math.log(q[c] / (1 - q[c])) for c in cfg["selected_features"]])
    return float(expit(np.dot(z, np.asarray(cfg["coef"])) + cfg["intercept"]))


def tide_trigger(astro_m: float, model: dict) -> float:
    """Mức triều T từ mực triều thiên văn Vũng Tàu của giờ đó. `model` là m2_<thành phố>_tide.json."""
    if model["kind"] == "zero":
        return 0.0
    if model["kind"] != "percentile":
        raise ValueError(f"Chưa hỗ trợ kiểu mô hình triều: {model['kind']}")
    values = np.asarray(model["climatology_q"], float)
    p = np.interp(np.asarray([astro_m], float), values, np.linspace(0, 1, len(values)), left=0, right=1)
    return float(expit((p - .95) / .02).astype(np.float32)[0])
