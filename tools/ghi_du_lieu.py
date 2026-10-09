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
import threading
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
RADAR_READY_S = 420  # ảnh radar có trên cổng 3 tới 6 phút sau giờ ghi trên ảnh (đo sáng 09/10): mỗi lượt chạy ở phút thứ 7 của mốc 10 phút
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


def within(seconds: float, fn, *args):
    """Chạy một bước với hạn chót. Từng lần gọi mạng đã có giới hạn, nhưng 21:31 tối 08/10 cổng trạm đo giữ kết nối mở
    hơn một giờ và cả bộ ghi đứng theo. Quá hạn thì bỏ bước đó (luồng kẹt tự chết khi tắt chương trình), chu kỳ đi tiếp."""
    box: dict = {}

    def run() -> None:
        try:
            box["value"] = fn(*args)
        except BaseException as exc:  # noqa: BLE001  - chuyển nguyên lỗi về luồng chính
            box["error"] = exc

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        raise TimeoutError(f"quá {seconds:g} giây")
    if "error" in box:
        raise box["error"]
    return box.get("value")


def save_radar(day: Path) -> int:
    saved = 0
    utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    utc = utc.replace(minute=utc.minute // 10 * 10)
    for back in (0, 10, 20, 30):  # 0: ảnh của mốc vừa qua; trước đây bỏ qua nên radar luôn cũ thêm 10 phút
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


SCAN_PER_CYCLE = 3  # số camera nhờ Gemini đọc mỗi lượt: hạn mức miễn phí chỉ vài chục lần gọi một ngày
SCAN_GAP = timedelta(minutes=30)  # không đọc lại một camera sớm hơn thế
_scanned: dict[str, datetime] = {}


def radar_step(now: datetime) -> str:
    """Đổi các ảnh radar của giờ qua thành trạng thái mưa của từng tuyến, ghi ra file cho máy chủ trên máy này và gửi lên máy chủ trên mạng.

    Sau đó nhờ máy chủ cho Gemini đọc vài camera nằm trong khu radar thấy mưa lớn, để xác nhận hoặc gỡ (ghi chú 11, QĐ4).
    """
    from floodrisk import config as fr_config
    from floodrisk.live import radar

    utc = now.astimezone(timezone.utc)
    folders = [LIVE / f"{(now - timedelta(days=d)):%Y-%m-%d}" / "radar" for d in (0, 1)]
    images = radar.last_hour(folders, utc)
    if len(images) < radar.MIN_IMAGES:
        return f"radar chỉ có {len(images)} ảnh trong giờ qua"
    background = radar.dry_background()
    rate = radar.hourly_rate([radar.levels(p) for p in images], background)
    routes = pd.read_parquet(fr_config.route_table_path("hcm"), columns=["lat", "lon", "band_rain"])
    state = radar.states_at(routes.lat.to_numpy(), routes.lon.to_numpy(), rate)
    state[routes.band_rain.to_numpy() == 0] = 0  # tuyến mô hình không xếp là dễ ngập do mưa thì không bao giờ có mức do mưa
    record = {"at": utc.isoformat(timespec="seconds"), "image_time": radar.image_time(images[-1]).isoformat(timespec="seconds"),
              "images": len(images), "watch": np.flatnonzero(state == 1).tolist(), "alert": np.flatnonzero(state == 2).tolist()}
    (LIVE / "radar_state_hcm.json").write_text(json.dumps(record), encoding="utf-8")
    note = f"radar {len(images)} ảnh: {len(record['watch'])} tuyến cảnh giác, {len(record['alert'])} báo động"
    if background is None:
        note += " (CHƯA TRỪ NỀN KHÔ: chạy tools/dung_nen_kho_radar.py)"

    url, token = env_value("RISK_PUSH_URL").rstrip("/"), env_value("RISK_PUSH_TOKEN")
    if not url or not token:
        return note
    r = httpx.post(url + "/api/risk/radar", json={"city": "hcm", "state": record}, headers={"X-Push-Token": token}, timeout=60)
    note += f"; gửi radar HTTP {r.status_code}"

    cams = [c for c in httpx.get(url + "/api/cameras", params={"city": "hcm"}, timeout=60).json() if c["has_image"]]
    if not cams:
        return note
    wet = radar.states_at([c["lat"] for c in cams], [c["lon"] for c in cams], rate)
    due = [(int(s), c) for s, c in zip(wet, cams) if s > 0 and now - _scanned.get(c["id"], now - SCAN_GAP) >= SCAN_GAP]
    due.sort(key=lambda sc: -sc[0])  # khu báo động trước
    read = []
    for _, cam in due[:SCAN_PER_CYCLE]:
        _scanned[cam["id"]] = now
        try:
            got = httpx.post(url + f"/api/cameras/{cam['id']}/read", timeout=150)
        except httpx.HTTPError as exc:
            read.append(f"{cam['name']}: lỗi {type(exc).__name__}")
            continue
        if got.status_code != 200:
            read.append(f"{cam['name']}: HTTP {got.status_code}")
            if got.status_code == 503:  # hết khóa hoặc hết hạn mức Gemini: thôi không gọi tiếp lượt này
                break
            continue
        reading = got.json()["reading"]
        append(LIVE / f"{now:%Y-%m-%d}" / "camera_readings.jsonl", {"at": now.isoformat(timespec="seconds"), "camera": cam, "reading": reading})
        read.append(f"{cam['name']}: {'NGẬP ' + str(reading.get('depth_class')) if reading.get('flooded') else reading.get('depth_class')}")
    return note + f"; camera trong khu mưa {int((wet > 0).sum())}" + (", Gemini đọc " + " | ".join(read) if read else "")


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
        parts.append(f"radar +{within(120, save_radar, day)}")
    except Exception as exc:
        parts.append(f"radar lỗi {type(exc).__name__}")
    try:
        parts.append(within(600, radar_step, now))  # ba lần Gemini đọc camera có thể mất tới ba phút
    except Exception as exc:
        parts.append(f"radar lỗi {type(exc).__name__}: {exc}")
    tide, wettest = None, 0.0
    try:
        tide, wettest = within(180, save_hydro, day, now)
        parts.append(f"triều {tide:.2f} m" if tide is not None else "triều ?")
        parts.append(f"mưa giờ qua lớn nhất {wettest:g} mm")
    except Exception as exc:
        parts.append(f"hydro lỗi {type(exc).__name__}")
    if last_model_hour != now.hour:
        try:
            parts.append("mô hình " + within(180, save_model, day, now))
            last_model_hour = now.hour
        except Exception as exc:
            parts.append(f"mô hình lỗi {type(exc).__name__}")
    # Đẩy ở mọi lượt, không chỉ đầu giờ: máy chủ miễn phí ngủ sau 15 phút không ai gọi và mất bản tính khi khởi động lại.
    try:
        pushed = within(120, push_model)
        if pushed:
            parts.append(pushed)
    except Exception as exc:
        parts.append(f"đẩy mức lỗi {type(exc).__name__}")
    active = (tide is not None and tide >= TIDE_ACTIVE_M) or wettest >= RAIN_ACTIVE_MM
    if active or now.minute < 10:
        try:
            ok, total = within(300, save_cameras, day, now)
            parts.append(f"camera {ok}/{total}" + (" (đang có mưa hoặc triều cao)" if active else ""))
        except Exception as exc:
            parts.append(f"camera lỗi {type(exc).__name__}")
    log("; ".join(parts))
    return last_model_hour


def seconds_to_next_cycle(now_s: float) -> float:
    """Số giây chờ tới lượt kế: RADAR_READY_S sau mốc 10 phút gần nhất sắp tới. Còn dưới 2 phút thì đợi mốc sau, để hai lượt không dính nhau."""
    wait = (RADAR_READY_S - now_s % STEP_S) % STEP_S
    return wait if wait >= 120 else wait + STEP_S


def main() -> None:
    LIVE.mkdir(parents=True, exist_ok=True)
    log("bắt đầu ghi; tạo file data/raw/live/STOP để dừng")
    last_model_hour = None
    while not (LIVE / "STOP").exists():
        last_model_hour = cycle(last_model_hour)
        time.sleep(seconds_to_next_cycle(time.time()))
    log("thấy file STOP, dừng")


if __name__ == "__main__":
    main()
