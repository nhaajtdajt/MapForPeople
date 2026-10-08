"""Mức nguy cơ lúc này của một thành phố, tính từ các file mô hình trong data/model/ (ghi chú 11, QĐ1).

Cho ra đúng kết quả của `scripts/run_hourly.py` trong repo flood_prediction_models (commit 842da0a),
nhưng không dựng bảng 420.000 dòng: giữ nhóm của từng tuyến và chỉ tính hai trạng thái của ngày.
Kiểm bằng `tools/so_voi_run_hourly.py`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from floodrisk import config
from floodrisk.model import levels, trigger

RainFetch = Callable[[str, str], pd.Series]  # (tên thành phố trong repo mô hình, mô hình thời tiết) -> mưa từng giờ


@dataclass(frozen=True)
class Cause:
    state: int  # 0 yên, 1 cảnh giác, 2 báo động
    trigger: float  # giá trị T của mô hình
    inputs: dict  # số liệu đưa vào: mưa 3 giờ và 24 giờ, hoặc mực triều thiên văn


@dataclass(frozen=True)
class Hour:
    valid_time: pd.Timestamp
    rain: Cause
    tide: Cause


@dataclass(frozen=True)
class Snapshot:
    city: str
    model_version: str
    generated_at: pd.Timestamp
    rain_source: str
    hours: tuple[Hour, ...]  # giờ này, +1 giờ, +2 giờ


def current_hour() -> pd.Timestamp:
    """Giờ hiện tại theo giờ Việt Nam, làm tròn xuống đầu giờ: giờ mà một bản tính mới sẽ mang."""
    return pd.Timestamp.now(tz=trigger.TZ).floor("h")


def to_record(snapshot: Snapshot) -> dict:
    """Một bản tính ở dạng lưu được ra file JSON."""
    def cause(c: Cause) -> dict:
        return {"state": c.state, "trigger": c.trigger, "inputs": c.inputs}

    return {"city": snapshot.city, "model_version": snapshot.model_version, "generated_at": snapshot.generated_at.isoformat(),
            "rain_source": snapshot.rain_source,
            "hours": [{"valid_time": h.valid_time.isoformat(), "rain": cause(h.rain), "tide": cause(h.tide)} for h in snapshot.hours]}


def from_record(record: dict) -> Snapshot:
    def cause(c: dict) -> Cause:
        return Cause(int(c["state"]), float(c["trigger"]), dict(c["inputs"]))

    hours = tuple(Hour(pd.Timestamp(h["valid_time"]), cause(h["rain"]), cause(h["tide"])) for h in record["hours"])
    return Snapshot(record["city"], record["model_version"], pd.Timestamp(record["generated_at"]), record["rain_source"], hours)


def _read_json(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CityModel:
    """Các file mô hình của một thành phố, nạp một lần."""

    def __init__(self, city: str):
        slug = config.MODEL_CITY[city]
        root = config.model_dir()
        version = root / config.MODEL_VERSION
        self.city, self.slug = city, slug
        # Bảng tuyến được đọc trước: thành phố chưa dựng (tools/dung_lop_mo_hinh.py) thì báo thiếu file ngay ở đây.
        self.routes = pd.read_parquet(config.route_table_path(city))
        self.bands_rain = self.routes.band_rain.to_numpy(np.uint8)
        self.bands_tide = self.routes.band_tide.to_numpy(np.uint8)
        self.rain_cfg = _read_json(version / "rain_trigger.json")
        final = _read_json(root / "final_config.json")
        self.rain_limits = (float(final["q_watch"]), float(final["q_alert"]))
        tide_limits = _read_json(root / "combination_thresholds.json")["thresholds"][slug]["tide"]
        self.tide_limits = (float(tide_limits["t_lo"]), float(tide_limits["t_hi"]))
        self.tide_model = _read_json(root / f"m2_{slug}_tide.json")
        self.references = {source: pd.read_parquet(version / "cdfs" / f"{slug}_{source}_reference.parquet")
                           for source in ("ifs", "era5")}
        self.astro = None
        if self.tide_model["kind"] != "zero":
            tide = pd.read_parquet(config.tide_hourly_path(city))
            self.astro = pd.Series(tide.astro_m.to_numpy(float), index=pd.to_datetime(tide.time_utc, utc=True))

    def _rain(self, fetch: RainFetch) -> tuple[pd.Series, str, str]:
        try:
            return fetch(self.slug, "ecmwf_ifs"), "ifs", "Open-Meteo ecmwf_ifs"
        except trigger.ModelUnavailable:
            # Như bản gốc: chỉ đổi sang mô hình mặc định khi Open-Meteo không phục vụ IFS, và khi đó dùng bảng tham chiếu ERA5.
            return fetch(self.slug, "best_match"), "era5", "Open-Meteo best_match (IFS không có)"

    def snapshot(self, at=None, fetch: RainFetch = trigger.fetch_rain) -> Snapshot:
        now = pd.Timestamp.now(tz=trigger.TZ)
        at = now if at is None else pd.Timestamp(at)
        at = (at.tz_localize(trigger.TZ) if at.tzinfo is None else at.tz_convert(trigger.TZ)).floor("h")
        series, reference, source = self._rain(fetch)
        hours = []
        for window in trigger.rain_windows(series, at):
            t_rain = trigger.rain_trigger(window["rain_max_3h_mm"], window["rain_total_mm"], self.rain_cfg, self.references[reference])
            rain = Cause(levels.day_state(t_rain, *self.rain_limits), t_rain,
                         {"max_3h_mm": round(window["rain_max_3h_mm"], 2), "total_24h_mm": round(window["rain_total_mm"], 2)})
            hours.append(Hour(window["valid_time"], rain, self._tide(window["valid_time"])))
        return Snapshot(self.city, config.MODEL_VERSION, now, source, tuple(hours))

    def snapshot_without_rain(self, at=None) -> Snapshot:
        """Bản tính khi chưa lấy được mưa cho mô hình: triều vẫn tính đủ (không cần mạng), mưa để ở trạng thái yên và đánh dấu thiếu.

        Dùng lúc máy chủ vừa khởi động mà nguồn mưa lỗi, để trạm mưa, mực nước Phú An và báo cáo vẫn nâng được mức.
        """
        now = pd.Timestamp.now(tz=trigger.TZ)
        at = now if at is None else pd.Timestamp(at)
        at = (at.tz_localize(trigger.TZ) if at.tzinfo is None else at.tz_convert(trigger.TZ)).floor("h")
        hours = tuple(Hour(at + pd.Timedelta(hours=h), Cause(levels.QUIET, 0.0, {"missing": True}), self._tide(at + pd.Timedelta(hours=h)))
                      for h in trigger.HORIZONS)
        return Snapshot(self.city, config.MODEL_VERSION, now, "chưa lấy được mưa cho mô hình", hours)

    def _tide(self, valid_time: pd.Timestamp) -> Cause:
        if self.astro is None:
            return Cause(levels.QUIET, 0.0, {})
        key = valid_time.tz_convert("UTC")
        if key not in self.astro.index:
            raise ValueError(f"Bảng triều thiên văn không có giờ {valid_time}; cần dựng lại bằng tools/dung_lop_mo_hinh.py")
        astro_m = float(self.astro.loc[key])
        t_tide = trigger.tide_trigger(astro_m, self.tide_model)
        return Cause(levels.day_state(t_tide, *self.tide_limits), t_tide, {"astro_m": round(astro_m, 3)})

    def levels(self, hour: Hour) -> np.ndarray:
        """Mức của từng tuyến (0 thấp, 1 vừa, 2 cao), theo thứ tự dòng của bảng tuyến."""
        return levels.route_levels(self.bands_rain, self.bands_tide, hour.rain.state, hour.tide.state)

    def counts(self, hour: Hour) -> dict[str, int]:
        level = self.levels(hour)
        return {"high": int((level == levels.HIGH).sum()), "medium": int((level == levels.MEDIUM).sum())}
