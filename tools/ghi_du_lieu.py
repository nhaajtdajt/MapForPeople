"""Bộ ghi tạm: lưu lại số liệu lúc này để sau còn kiểm mô hình và phát lại (ghi chú 11, mục 5).

    python tools/ghi_du_lieu.py

Mỗi 10 phút ghi vào data/raw/live/NGÀY/ (thư mục này không vào git):
- radar/         ảnh radar Nhà Bè (cổng chỉ giữ ảnh khoảng một ngày);
- hydro.jsonl    mực nước Phú An và mưa từng giờ của các trạm ở TP.HCM;
- model.jsonl    mỗi giờ: mức mưa mà Mô hình 2 tính ra cho hai thành phố;
- cams/GIỜPHÚT/  ảnh của các camera nằm sát tuyến từng ngập (data/raw/live/watchlist.json).
  Ảnh được chụp mỗi 10 phút khi triều từ 1,30 m hoặc có trạm đo từ 5 mm trong giờ gần nhất; lúc khác thì mỗi giờ một lần.

Dừng: tạo file data/raw/live/STOP (hoặc tắt tiến trình).

Đây là bản tạm. Nó mượn thẳng mã hydro.py và cameras.py trong repo mlai-car-access nằm cạnh repo này,
và đọc file mô hình trong repo flood_prediction_models; khi hai phần đó được chép vào repo này thì sửa lại chỗ nhập.
"""
from __future__ import annotations

import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIBLINGS = ROOT.parent
sys.path.insert(0, str(SIBLINGS / "mlai-car-access" / "backend"))
from app import cameras, hydro  # noqa: E402

LIVE = ROOT / "data" / "raw" / "live"
MODEL = SIBLINGS / "flood_prediction_models" / "models"
VN = timezone(timedelta(hours=7))
UA = {"User-Agent": "floodrisk-hackathon/0.1 (bo ghi du lieu)"}
STEP_S = 600
TIDE_ACTIVE_M = 1.30
RAIN_ACTIVE_MM = 5.0
RADAR = "http://hymetnet.gov.vn/dataout_web/NHB/{d:%Y%m%d}/NHB_{d:%Y%m%d%H%M}_CMAX00.png"
GRID = {"ho_chi_minh": ((106.4363502282, 10.55, 107.0, 11.05), 3, 3), "da_nang": ((108.0331223, 15.8181984, 108.35, 16.1601221), 2, 3)}


def log(text: str) -> None:
    line = f"{datetime.now(VN):%d/%m %H:%M:%S} {text}"
    print(line, flush=True)
    with open(LIVE / "recorder.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def append(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def save_radar(day: Path) -> int:
    saved = 0
    utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    utc = utc.replace(minute=utc.minute // 10 * 10)
    for back in (10, 20, 30):
        t = utc - timedelta(minutes=back)
        out = day / "radar" / f"NHB_{t:%Y%m%d%H%M}.png"
        if out.exists():
            continue
        r = httpx.get(RADAR.format(d=t), headers=UA, timeout=30)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(r.content)
            saved += 1
    return saved


def save_hydro(day: Path, now: datetime) -> tuple[float | None, float]:
    tide = hydro.tide_point(now)
    readings = hydro.tide_readings()
    wettest = 0.0
    gauges = []
    for g in hydro.rain_gauges():
        hours = [(t, v) for t, v in hydro.gauge_hours(g) if t > now - timedelta(hours=3)]
        last = [v for t, v in hours if t > now - timedelta(minutes=70)]
        wettest = max(wettest, max(last, default=0.0))
        gauges.append({"id": g["id"], "name": g["name"], "lat": g["lat"], "lon": g["lon"], "hours": [[t.isoformat(), v] for t, v in hours]})
    append(day / "hydro.jsonl", {"at": now.isoformat(timespec="seconds"), "tide_m": tide and round(tide[0], 3), "tide_kind": tide and tide[1],
                                 "tide_last_reading": readings[-1] if readings else None, "wettest_last_hour_mm": wettest, "gauges": gauges})
    return (tide[0] if tide else None), wettest


def save_model(day: Path, now: datetime) -> str:
    cfg = json.loads((MODEL / "final_2025-01-01" / "rain_trigger.json").read_text())
    final = json.loads((MODEL / "final_config.json").read_text())
    summary = []
    for city, ((w, s, e, n), ny, nx) in GRID.items():
        pts = [(float(y), float(x)) for y in np.linspace(s, n, ny) for x in np.linspace(w, e, nx)]
        r = httpx.get("https://api.open-meteo.com/v1/forecast", headers=UA, timeout=90, params={
            "latitude": ",".join(f"{a:.6f}" for a, b in pts), "longitude": ",".join(f"{b:.6f}" for a, b in pts),
            "hourly": "precipitation", "past_hours": 72, "forecast_hours": 12, "timezone": "Asia/Ho_Chi_Minh", "models": "ecmwf_ifs"})
        r.raise_for_status()
        items = r.json()
        items = items if isinstance(items, list) else [items]
        series = pd.concat([pd.Series(pd.to_numeric(pd.Series(it["hourly"]["precipitation"]), errors="coerce").to_numpy(),
                                      index=pd.to_datetime(it["hourly"]["time"])) for it in items], axis=1).max(axis=1).sort_index()
        ref = pd.read_parquet(MODEL / "final_2025-01-01" / "cdfs" / f"{city}_ifs_reference.parquet")
        at = pd.Timestamp(now.replace(tzinfo=None)).floor("h")
        rows = []
        for h in range(3):
            t = at + pd.Timedelta(hours=h)
            sub = series.loc[(series.index > t - pd.Timedelta(hours=6)) & (series.index <= t)].dropna()
            total = float(series.loc[(series.index > t - pd.Timedelta(hours=24)) & (series.index <= t)].dropna().sum())
            max3 = float(sub.rolling(3, min_periods=3).sum().max())
            q = {}
            for col, value in (("rain_max_3h_mm", max3), ("rain_total_mm", total)):
                x = np.sort(ref[col].dropna().to_numpy(float))
                q[col] = float(np.clip(np.searchsorted(x, value, side="right") / max(1, len(x)), .001, .999))
            z = sum(c * math.log(q[k] / (1 - q[k])) for k, c in zip(cfg["selected_features"], cfg["coef"])) + cfg["intercept"]
            trigger = 1 / (1 + math.exp(-z))
            state = "quiet" if trigger < final["q_watch"] else "watch" if trigger < final["q_alert"] else "alert"
            rows.append({"valid": t.isoformat(), "h": h, "max3h_mm": round(max3, 2), "total24_mm": round(total, 2), "T_rain": round(trigger, 5), "state": state})
        append(day / "model.jsonl", {"at": now.isoformat(timespec="seconds"), "city": city, "source": "Open-Meteo ecmwf_ifs", "rows": rows})
        summary.append(f"{city}:{rows[0]['state']}")
    return ", ".join(summary)


def env_value(name: str) -> str:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    return ""


def push_model() -> str:
    """Tính mức của mô hình cho TP.HCM rồi đẩy lên máy chủ đang chạy trên mạng, nơi không gọi được Open-Meteo.

    Chỉ chạy khi .env có RISK_PUSH_URL và RISK_PUSH_TOKEN (cùng giá trị với biến RISK_PUSH_TOKEN đặt trên máy chủ).
    """
    url, token = env_value("RISK_PUSH_URL"), env_value("RISK_PUSH_TOKEN")
    if not url or not token:
        return ""
    from floodrisk.model.live import CityModel, to_record

    record = to_record(CityModel("hcm").snapshot())
    r = httpx.post(url.rstrip("/") + "/api/risk/snapshot", json={"city": "hcm", "record": record},
                   headers={"X-Push-Token": token}, timeout=60)
    return f"đẩy mức lên máy chủ: HTTP {r.status_code}"


def save_cameras(day: Path, now: datetime) -> tuple[int, int]:
    wl = json.loads((LIVE / "watchlist.json").read_text(encoding="utf-8"))["cameras"]
    folder = day / "cams" / f"{now:%H%M}"
    folder.mkdir(parents=True, exist_ok=True)

    def one(cam: dict) -> bool:
        img = cameras.snapshot(cam["id"], max_age_s=0)
        if img:
            (folder / f"{cam['id']}.jpg").write_bytes(img)
        return bool(img)

    with ThreadPoolExecutor(8) as pool:
        got = list(pool.map(one, wl))
        missed = [cam for cam, ok in zip(wl, got) if not ok]
        if missed:  # cổng đôi lúc trả chậm khi hỏi dồn: thử lại một lượt cho những camera hụt
            time.sleep(3)
            got = [ok for ok in got if ok] + list(pool.map(one, missed))
    return sum(got), len(wl)


def cycle(last_model_hour: int | None) -> int | None:
    now = datetime.now(VN)
    day = LIVE / f"{now:%Y-%m-%d}"
    parts = []
    try:
        parts.append(f"radar +{save_radar(day)}")
    except Exception as exc:
        parts.append(f"radar lỗi {type(exc).__name__}")
    tide, wettest = None, 0.0
    try:
        tide, wettest = save_hydro(day, now)
        parts.append(f"triều {tide:.2f} m" if tide is not None else "triều ?")
        parts.append(f"mưa giờ qua lớn nhất {wettest:g} mm")
    except Exception as exc:
        parts.append(f"hydro lỗi {type(exc).__name__}")
    if last_model_hour != now.hour:
        try:
            parts.append("mô hình " + save_model(day, now))
            last_model_hour = now.hour
        except Exception as exc:
            parts.append(f"mô hình lỗi {type(exc).__name__}")
        try:
            pushed = push_model()
            if pushed:
                parts.append(pushed)
        except Exception as exc:
            parts.append(f"đẩy mức lỗi {type(exc).__name__}")
    active = (tide is not None and tide >= TIDE_ACTIVE_M) or wettest >= RAIN_ACTIVE_MM
    if active or now.minute < 10:
        try:
            ok, total = save_cameras(day, now)
            parts.append(f"camera {ok}/{total}" + (" (đang có mưa hoặc triều cao)" if active else ""))
        except Exception as exc:
            parts.append(f"camera lỗi {type(exc).__name__}")
    log("; ".join(parts))
    return last_model_hour


def main() -> None:
    LIVE.mkdir(parents=True, exist_ok=True)
    log("bắt đầu ghi; tạo file data/raw/live/STOP để dừng")
    last_model_hour = None
    while not (LIVE / "STOP").exists():
        started = time.time()
        last_model_hour = cycle(last_model_hour)
        time.sleep(max(5.0, STEP_S - (time.time() - started) % STEP_S))
    log("thấy file STOP, dừng")


if __name__ == "__main__":
    main()
