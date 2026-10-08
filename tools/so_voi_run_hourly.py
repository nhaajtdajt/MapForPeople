"""So mức nguy cơ repo này tính ra với tác vụ gốc của repo mô hình, cùng một giờ (ghi chú 11, QĐ1).

    python tools/so_voi_run_hourly.py --city hcm [--at 2026-10-08T13:00]

Chạy `scripts/run_hourly.py` trong repo flood_prediction_models nằm cạnh repo này (mất khoảng một phút),
rồi so từng tuyến và từng giờ dự báo: mức mưa T, mức triều T, trạng thái của ngày, mức của tuyến.
Hai bên tự lấy mưa từ Open-Meteo cách nhau khoảng một phút, nên T mưa có thể lệch rất nhỏ nếu nguồn vừa cập nhật;
vì vậy mức của tuyến còn được so thêm một lần với trạng thái của chính bản gốc.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from floodrisk import config
from floodrisk.model import levels
from floodrisk.model.live import CityModel

ROOT = Path(__file__).resolve().parents[1]
MODEL_REPO = ROOT.parent / "flood_prediction_models"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--city", default="hcm", choices=sorted(config.MODEL_CITY))
    parser.add_argument("--at", help="giờ cần tính, giờ Việt Nam; mặc định là giờ hiện tại")
    args = parser.parse_args()
    slug = config.MODEL_CITY[args.city]
    at = (pd.Timestamp(args.at, tz="Asia/Ho_Chi_Minh") if args.at else pd.Timestamp.now(tz="Asia/Ho_Chi_Minh")).floor("h")

    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": str(MODEL_REPO / "src")}
    subprocess.run([sys.executable, "scripts/run_hourly.py", "--city", slug, "--at", at.isoformat()],
                   cwd=MODEL_REPO, env=env, check=True, stdout=subprocess.DEVNULL)
    original = pd.read_parquet(MODEL_REPO / "data" / "export" / slug / "risk_hourly.parquet")

    model = CityModel(args.city)
    snapshot = model.snapshot(at)
    ids = model.routes.route_id.to_numpy()
    wrong = 0
    for h, hour in enumerate(snapshot.hours):
        rows = original[original.horizon_h == h]
        if len(rows) != len(ids) or not (rows.route_id.to_numpy() == ids).all():
            print(f"+{h} giờ: danh sách tuyến của hai bên khác nhau ({len(rows)} và {len(ids)})")
            return 1
        theirs = rows.level.map({"low": 0, "medium": 1, "high": 2}).to_numpy()
        their_rain = levels.STATE_NAMES.index(rows.day_state_rain.iloc[0])
        their_tide = levels.STATE_NAMES.index(rows.day_state_tide.iloc[0])
        ours = model.levels(hour)
        by_their_states = levels.route_levels(model.bands_rain, model.bands_tide, their_rain, their_tide)
        d_rain = abs(hour.rain.trigger - float(rows.T_rain.iloc[0]))
        d_tide = abs(hour.tide.trigger - float(rows.T_tide.iloc[0]))
        same_states = (hour.rain.state, hour.tide.state) == (their_rain, their_tide)
        mismatch = int((ours != theirs).sum())
        rule_mismatch = int((by_their_states != theirs).sum())
        wrong += rule_mismatch + (0 if same_states else 1) + (d_tide > 1e-6)
        print(f"{hour.valid_time:%d/%m %H:%M} (+{h} giờ): mưa {levels.STATE_NAMES[hour.rain.state]} (T {hour.rain.trigger:.6f}, lệch bản gốc {d_rain:.1e}), "
              f"triều {levels.STATE_NAMES[hour.tide.state]} (T {hour.tide.trigger:.3e}, lệch {d_tide:.1e}) | trạng thái {'trùng' if same_states else 'KHÁC'} bản gốc | "
              f"tuyến mức cao {int((ours == 2).sum())}, vừa {int((ours == 1).sum())} | số tuyến lệch mức: {mismatch} "
              f"(theo trạng thái của bản gốc: {rule_mismatch}) trên {len(ids)}")
    print("KẾT QUẢ: trùng với run_hourly.py" if wrong == 0 else "KẾT QUẢ: CÓ CHỖ LỆCH, xem các dòng trên")
    return 0 if wrong == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
