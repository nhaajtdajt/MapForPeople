"""Triều và mưa đo trực tiếp ở TP.HCM: mực nước Phú An và mưa từng giờ của các trạm trên vndms.gov.vn.

Chép từ mlai-car-access, commit f000823, file `backend/app/hydro.py` (quyết định D35 của repo đó), giữ nguyên
phần đọc cổng, phần khớp mô hình triều và bộ nhớ đệm. Bỏ phần dự báo mưa theo điểm và `rain_spells`, vì repo này
đưa mưa của trạm qua hàm mức mưa của mô hình (ghi chú 11, QĐ4).

- `tide_point(t)`: mực nước Phú An lúc t và cách biết ("measured" giữa hai số đo, "model" sau số đo cuối, sai số ±0,15 m).
- `rain_gauges()`, `gauge_hours(g)`: các trạm báo từng giờ và mưa từng giờ của một trạm (giá trị là tổng của giờ kết thúc tại mốc đó).
"""
from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx


VN_TZ = timezone(timedelta(hours=7))
PORTAL = "https://vndms.gov.vn"
HEADERS = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest", "Referer": PORTAL + "/"}
TIDE_STATION = "71600"  # Phú An, sông Sài Gòn
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
MARINE_POINT = (10.25, 106.80)  # Soài Rạp mouth: best fit of three coastal points to Phú An (5 Oct 2026)
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
# Fit of 5 Oct 2026 (lag h, scale, offset), used when the portal cannot be reached.
DEFAULT_FIT = (2.5, 1.13, -0.68)
TIDE_MODEL_ERR_M = 0.15
TIDE_PIN_FADE_H = 6
RAIN_GAUGE_TYPES = {3: "VRAIN", 4: "Đo mưa nhân dân"}  # hourly networks; KTTV/TV stations report daily
RAIN_GAUGE_M = 5000
DRAIN_H = 1
HCMC = (10.35, 106.30, 11.20, 107.10)

_cache: dict[str, tuple[float, object]] = {}
_lock = threading.Lock()
_client: httpx.Client | None = None


def _cached(key: str, ttl: float, fn):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    try:
        val = fn()
    except Exception:
        val = None
    if val is None and hit:
        return hit[1]  # keep the last good answer while a source is down
    # A failure is retried after a minute, not after the full TTL.
    _cache[key] = (time.time() if val is not None else time.time() - ttl + 60, val)
    return val


def _portal() -> httpx.Client:
    """The portal answers its map data only to a visitor session, as its own map page does."""
    global _client
    with _lock:
        if _client is None:
            _client = httpx.Client(headers=HEADERS, timeout=15, follow_redirects=True)
            _client.get(PORTAL + "/")
        return _client


def _portal_json(method: str, path: str, **kw):
    global _client
    for _ in range(2):
        r = _portal().request(method, PORTAL + path, **kw)
        j = r.json() if r.status_code == 200 else None
        if j is not None and not (isinstance(j, dict) and j.get("error")):
            return j
        with _lock:
            _client = None  # session expired: open a new one
    return None


def _label_time(label: str, now: datetime) -> datetime:
    h, d, m = map(int, re.match(r"(\d+)h\s*(\d+)/(\d+)", label.strip()).groups())
    year = now.year - (1 if m > now.month + 1 else 0)
    return datetime(year, m, d, tzinfo=VN_TZ) + timedelta(hours=h)


def _series(station: str, source: str, days: int) -> list[tuple[datetime, float]]:
    j = _portal_json("POST", "/home/detailRain", data={"id": station, "source": source, "timeSelect": str(days)})
    if not j or not j.get("labels"):
        return []
    now = datetime.now(VN_TZ)
    out = []
    for lab, v in zip(j["labels"].split(","), j["value"].split(",")):
        try:
            out.append((_label_time(lab, now), float(v)))
        except (AttributeError, ValueError):
            continue
    return sorted(out)


# ---- tide -----------------------------------------------------------------------

def tide_readings() -> list[tuple[datetime, float]]:
    return _cached("tide_obs", 300, lambda: _series(TIDE_STATION, "Water", 7) or None) or []


def _marine() -> list[tuple[datetime, float]]:
    def get():
        j = httpx.get(MARINE_URL, timeout=15, params={
            "latitude": MARINE_POINT[0], "longitude": MARINE_POINT[1], "hourly": "sea_level_height_msl",
            "past_days": 8, "forecast_days": 7, "timezone": "Asia/Ho_Chi_Minh", "cell_selection": "sea"}).json()
        h = j["hourly"]
        return [(datetime.fromisoformat(t).replace(tzinfo=VN_TZ), v)
                for t, v in zip(h["time"], h["sea_level_height_msl"]) if v is not None] or None
    return _cached("marine", 3600, get) or []


def _interp(series: list[tuple[datetime, float]], t: datetime) -> float | None:
    for (t1, v1), (t2, v2) in zip(series, series[1:]):
        if t1 <= t <= t2:
            return v1 + (v2 - v1) * (t - t1) / (t2 - t1)
    return None


def _fit(obs, sea) -> tuple[float, float, float]:
    """Lag, scale and offset that best map the coastal model onto the Phú An readings (least squares)."""
    best = None
    for q in range(25):
        lag = q * 0.25
        pairs = [(m, v) for t, v in obs if (m := _interp(sea, t - timedelta(hours=lag))) is not None]
        n = len(pairs)
        if n < 8:
            continue
        sx, sy = sum(m for m, _ in pairs), sum(v for _, v in pairs)
        sxx, sxy = sum(m * m for m, _ in pairs), sum(m * v for m, v in pairs)
        den = n * sxx - sx * sx
        if not den:
            continue
        a = (n * sxy - sx * sy) / den
        b = (sy - a * sx) / n
        sse = sum((a * m + b - v) ** 2 for m, v in pairs)
        if best is None or sse < best[0]:
            best = (sse, lag, a, b)
    return best[1:] if best else DEFAULT_FIT


def _tide_model():
    obs, sea = tide_readings(), _marine()
    if not sea:
        return None
    fit = _cached("tide_fit", 900, lambda: _fit(obs, sea) if obs else DEFAULT_FIT) or DEFAULT_FIT
    lag, a, b = fit

    def model(t):
        m = _interp(sea, t - timedelta(hours=lag))
        return None if m is None else a * m + b
    pins = [(t, v - m) for t, v in obs if (m := model(t)) is not None]
    return model, pins, obs, fit


def tide_point(t: datetime) -> tuple[float, str] | None:
    """Phú An level at t and how it is known: "measured" (between two readings) or "model"."""
    tm = _tide_model()
    if not tm:
        return None
    model, pins, obs, _ = tm
    m = model(t)
    if m is None:
        return None
    if pins and pins[0][0] <= t <= pins[-1][0]:
        return m + _interp(pins, t), "measured"
    if pins and t > pins[-1][0]:
        fade = max(0.0, 1 - (t - pins[-1][0]).total_seconds() / 3600 / TIDE_PIN_FADE_H)
        return m + pins[-1][1] * fade, "model"
    return m, "model"


def tide_status() -> dict:
    tm = _tide_model()
    obs = tide_readings()
    last = obs[-1] if obs else None
    return {"station": "Phú An (sông Sài Gòn)", "source": "Hệ thống giám sát thiên tai Việt Nam (vndms.gov.vn)",
            "source_url": PORTAL, "live": bool(obs),
            "last_reading": {"t": last[0].isoformat(), "level_m": last[1]} if last else None,
            "readings": [{"t": t.isoformat(), "level_m": v} for t, v in obs],
            "model": "Open-Meteo sea level (Soài Rạp) fitted to Phú An" if tm else None,
            "fit": dict(zip(("lag_h", "scale", "offset_m"), [round(x, 3) for x in tm[3]])) if tm else None,
            "model_err_m": TIDE_MODEL_ERR_M}


# ---- rain -----------------------------------------------------------------------

def rain_gauges() -> list[dict]:
    def get():
        out = []
        s, w, n, e = HCMC
        for typ, network in RAIN_GAUGE_TYPES.items():
            j = _portal_json("GET", "/warning_rain", params={"lv1": 0, "lv2": 10000, "types": typ}) or {}
            for f in j.get("features", []):
                lon, lat = f["geometry"]["coordinates"][:2]
                m = re.search(r"showStationInfo\(`([^`]*)`,`([^`]*)`", f["properties"].get("popupInfo", ""))
                if m and s <= lat <= n and w <= lon <= e:
                    out.append({"id": m.group(1), "source": m.group(2), "name": f["properties"].get("label", ""),
                                "network": network, "lat": lat, "lon": lon})
        return out or None
    return _cached("gauges", 86400, get) or []


def gauge_hours(g: dict) -> list[tuple[datetime, float]]:
    """Rain per hour at a gauge; each value is the total of the hour ending at its time."""
    return _cached(f"rain:{g['id']}", 300, lambda: _series(g["id"], g["source"], 1) or None) or []
