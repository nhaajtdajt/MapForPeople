"""Dựng nền khô của radar Nhà Bè: mức "mưa" ảnh vẫn tô khi không trạm nào mưa (nhiễu mặt đất: cảng, sông, nhà cao tầng).

Giờ khô là giờ không trạm nào trong 44 trạm đo báo quá DRY_MM (cổng vndms giữ chừng hai ngày số đo). Lấy trung bình cường độ
của mọi ảnh trong các giờ đó, làm mượt ô BOX x BOX như lúc dùng, lưu data/processed/hcm/radar_nen_kho.npz.
Tối 08/10/2026: 36 ảnh khô; nền tại cảng Tân Thuận tới 30 mm/giờ, làm radar "báo động" 214 tuyến nhóm A trong khi trời chỉ
mưa vừa và camera thấy đường ướt. Chạy lại khi bộ ghi có thêm ngày khô:

    python tools/dung_nen_kho_radar.py
"""
import sys
from datetime import timedelta, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from floodrisk.live import hydro, radar  # noqa: E402

VN = timezone(timedelta(hours=7))
LIVE = ROOT / "data" / "raw" / "live"
DRY_MM = 0.5
MIN_IMAGES = 12


def gauge_hour_of(path: Path):
    """Giờ trạm đo (tính theo giờ kết thúc) chứa ảnh này."""
    return (radar.image_time(path).astimezone(VN) + timedelta(minutes=59)).replace(minute=0, second=0, microsecond=0)


def main() -> None:
    files = sorted(p for folder in LIVE.glob("20*") for p in (folder / "radar").glob("NHB_*.png"))
    city_max: dict = {}
    for g in hydro.rain_gauges():
        for t, v in hydro.gauge_hours(g):
            key = t.astimezone(VN).replace(minute=0, second=0, microsecond=0)
            city_max[key] = max(city_max.get(key, 0.0), float(v))
    dry = [p for p in files if gauge_hour_of(p) in city_max and city_max[gauge_hour_of(p)] <= DRY_MM]
    if len(dry) < MIN_IMAGES:
        sys.exit(f"chỉ có {len(dry)} ảnh trong giờ khô (cần {MIN_IMAGES}), chưa dựng nền")
    total = None
    for p in dry:
        rate = radar.RATE_MM_H[radar.levels(p)]
        total = rate if total is None else total + rate
    background = uniform_filter(total / len(dry), size=radar.BOX, mode="constant")
    out = radar.background_path()
    radar.save_background(background, out, images=len(dry))
    first, last = radar.image_time(dry[0]).astimezone(VN), radar.image_time(dry[-1]).astimezone(VN)
    print(f"{len(dry)} ảnh khô trong {len(files)} ảnh, từ {first:%d/%m %H:%M} tới {last:%d/%m %H:%M}")
    print(f"nền: lớn nhất {background.max():.1f} mm/giờ; điểm ảnh nền từ 8 mm/giờ: {(background >= 8).sum():,}; từ 20: {(background >= 20).sum():,}")
    print(f"đã ghi {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
