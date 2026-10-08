"""Radar thời tiết Nhà Bè: mưa đang rơi ở đâu, cập nhật 10 phút một lần.

Ảnh là sản phẩm CMAX của đài khí tượng (hymetnet.gov.vn), 2.310 x 2.310 điểm, 11 màu mưa. Ở đây:
- đổi màu ra cường độ mưa theo thang chuẩn (bậc k là 5 + 5k dBZ, rồi công thức Marshall-Palmer);
- lấy trung bình các ảnh của một giờ, rồi trung bình trong ô BOX x BOX điểm ảnh quanh mỗi vị trí;
- ra trạng thái yên, cảnh giác, báo động theo hai ngưỡng trên thang của radar.

Vị trí đặt ảnh lên bản đồ (KM_PER_PX, SHIFT_PX) được chỉnh theo 44 trạm đo mưa trên dữ liệu ngày 08/10/2026 (144 ảnh, 1.056
cặp trạm-giờ): phân biệt giờ trạm từ 15 mm với giờ dưới 5 mm đạt 0,97–1,00. Radar ước mưa to thấp hơn trạm đo khoảng 1,4 lần
(trung vị tỉ số trạm/radar ở các giờ trạm từ 15 mm), nên hai ngưỡng của nó là ngưỡng mm của trạm (local.py) chia 1,4.
Ở ngưỡng 20 radar bắt 7 trong 19 giờ trạm từ 15 mm và không lần nào báo khi trạm dưới 5 mm.
Mới có một ngày dữ liệu: các con số này phải được kiểm lại khi bộ ghi có thêm ngày mưa.

Nền khô: trong 12 km quanh trạm radar, ảnh tô "mưa" cả khi trời khô (cảng Tân Thuận, sông, nhà cao tầng Q7: tới 30 mm/giờ),
và tối 08/10 toàn bộ 214 tuyến nhóm A bị radar đưa lên báo động đều nằm trên nền đó. 44 trạm đo không bắt được vì chỉ 5 trạm
ở trong 15 km và cả 5 nằm trên nền thấp. `dry_background()` đọc bản đồ nền dựng từ các giờ không trạm nào mưa
(tools/dung_nen_kho_radar.py); `hourly_rate` trừ nó đi trước khi so ngưỡng.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter

from floodrisk import config

SITE = (10.6589, 106.7286)  # trạm radar Nhà Bè (vĩ độ, kinh độ)
KM_PER_PX = 0.26
SHIFT_PX = (-8, -4)  # (cột, hàng) cộng thêm khi đặt một điểm lên ảnh; khớp nhất với trạm đo ngày 08/10
BOX = 9  # ô lấy trung bình quanh mỗi vị trí, khoảng 2,3 km
WATCH_MM_H = 20.0  # ngưỡng trạm đo (local.GAUGE_WATCH[0] = 30 mm/giờ) chia 1,4; trước là 8
ALERT_MM_H = 35.0  # local.GAUGE_ALERT[0] = 50 mm/giờ chia 1,4; trước là 20 (và 12 cho tới tối 08/10)
MIN_IMAGES = 4  # cần ít nhất chừng này ảnh trong giờ qua
NEAR_SITE_KM = 5.0  # sát trạm radar toàn nhiễu mặt đất
BACKGROUND_STEP = 0.25  # file nền khô lưu uint8 theo bước này (mm/giờ), tối đa 63,75
URL = "http://hymetnet.gov.vn/dataout_web/NHB/{d:%Y%m%d}/NHB_{d:%Y%m%d%H%M}_CMAX00.png"
PALETTE = [(102, 212, 251), (2, 109, 248), (7, 69, 248), (167, 250, 132), (87, 250, 35), (5, 224, 51),
           (255, 216, 0), (255, 166, 0), (253, 129, 19), (255, 28, 0), (204, 0, 113)]  # từ mưa yếu tới mưa mạnh
_DBZ = np.array([0.0] + [5.0 + 5.0 * k for k in range(1, len(PALETTE) + 1)])
RATE_MM_H = np.where(_DBZ > 0, (10 ** (_DBZ / 10) / 200) ** (1 / 1.6), 0.0).astype(np.float32)
RATE_MM_H[0] = 0.0


def image_time(path: Path) -> datetime:
    """Giờ của ảnh (UTC), lấy từ tên file NHB_YYYYMMDDHHMM.png."""
    return datetime.strptime(path.stem[4:16], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)


def levels(path: Path) -> np.ndarray:
    """Bậc mưa của từng điểm ảnh: 0 là không mưa, 1 tới 11 theo PALETTE."""
    import rasterio  # chỉ máy xử lý radar mới cần thư viện này

    with rasterio.open(path) as src:
        data = src.read()
        if data.shape[0] == 1:
            table = np.zeros(256, np.uint8)
            for index, colour in src.colormap(1).items():
                if tuple(colour[:3]) in PALETTE:
                    table[index] = PALETTE.index(tuple(colour[:3])) + 1
            return table[data[0]]
        rgb = np.moveaxis(data[:3], 0, -1).astype(np.int32)
        key = rgb[..., 0] * 65536 + rgb[..., 1] * 256 + rgb[..., 2]
        out = np.zeros(key.shape, np.uint8)
        for k, (r, g, b) in enumerate(PALETTE, 1):
            out[key == r * 65536 + g * 256 + b] = k
        return out


def last_hour(folders: list[Path], now: datetime) -> list[Path]:
    """Các ảnh radar của 65 phút vừa qua trong những thư mục đã cho, cũ trước mới sau."""
    found = [p for folder in folders if folder.exists() for p in folder.glob("NHB_*.png")]
    recent = [p for p in found if timedelta(0) <= now - image_time(p) <= timedelta(minutes=65)]
    return sorted(recent, key=image_time)


def background_path() -> Path:
    return config.processed_dir("hcm") / "radar_nen_kho.npz"


def save_background(background: np.ndarray, path: Path, images: int) -> None:
    """Ghi nền khô (đã làm mượt ô BOX x BOX) thành file nhỏ: uint8 theo bước BACKGROUND_STEP, nén."""
    quantised = np.clip(np.round(np.asarray(background, np.float32) / BACKGROUND_STEP), 0, 255).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, nen=quantised, buoc=BACKGROUND_STEP, so_anh=images)


def dry_background(path: Path | None = None) -> np.ndarray | None:
    """Nền khô của ảnh radar (mm/giờ, cùng cỡ ảnh), hoặc None khi chưa dựng."""
    path = path or background_path()
    if not path.exists():
        return None
    with np.load(path) as f:
        return f["nen"].astype(np.float32) * float(f["buoc"])


def hourly_rate(grids: list[np.ndarray], background: np.ndarray | None = None) -> np.ndarray:
    """Cường độ mưa trung bình của giờ qua (mm/giờ trên thang radar), đã làm mượt trong ô BOX x BOX.

    Có `background` (nền khô, xem `dry_background`) thì trừ đi, không để âm: phần còn lại mới là mưa đang rơi.
    """
    mean = np.mean([RATE_MM_H[g] for g in grids], axis=0, dtype=np.float32)
    smooth = uniform_filter(mean, size=BOX, mode="constant")
    return smooth if background is None else np.maximum(smooth - background, 0.0)


def states_at(lat, lon, rate: np.ndarray) -> np.ndarray:
    """Trạng thái mưa theo radar tại từng vị trí: 0 yên, 1 cảnh giác, 2 báo động. Ngoài ảnh hoặc sát trạm radar thì là 0."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    east_km = (lon - SITE[1]) * 111.32 * np.cos(np.radians(SITE[0]))
    north_km = (lat - SITE[0]) * 110.54
    centre = rate.shape[0] // 2
    col = np.round(centre + east_km / KM_PER_PX).astype(int) + SHIFT_PX[0]
    row = np.round(centre - north_km / KM_PER_PX).astype(int) + SHIFT_PX[1]
    usable = (col >= 0) & (col < rate.shape[1]) & (row >= 0) & (row < rate.shape[0]) & (np.hypot(east_km, north_km) > NEAR_SITE_KM)
    value = np.zeros(lat.shape, np.float32)
    value[usable] = rate[row[usable], col[usable]]
    return np.where(value >= ALERT_MM_H, 2, np.where(value >= WATCH_MM_H, 1, 0)).astype(np.uint8)
