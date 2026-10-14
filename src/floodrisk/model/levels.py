"""Nhóm tuyến, trạng thái ngày và mức nguy cơ, đúng như tác vụ mỗi giờ của repo mô hình.

Chép từ flood_prediction_models, commit 842da0a:
- `route_bands`: nguyên văn `src/floodrisk/combine.py`;
- `day_state`, `route_levels`: quy tắc ở `scripts/run_hourly.py`, dòng 119-121.

Không sửa quy tắc ở đây. Mô hình đổi thì chép lại từ repo gốc (ghi chú 11, QĐ1).
"""
from __future__ import annotations

import numpy as np

QUIET, WATCH, ALERT = 0, 1, 2
STATE_NAMES = ("quiet", "watch", "alert")
LOW, MEDIUM, HIGH = 0, 1, 2
LEVEL_NAMES = ("low", "medium", "high")
BAND_NAMES = ("C", "B", "A")  # theo mã nhóm 0, 1, 2


def route_bands(score, tie, mask) -> np.ndarray:
    """Nhóm của từng tuyến: 2 = 5% điểm cao nhất (nhóm A), 1 = 15% kế tiếp (nhóm B), 0 = còn lại.

    Chỉ xếp trong các tuyến có `mask` đúng. Điểm bằng nhau thì xét `tie`, rồi tới thứ tự dòng.
    """
    ids = np.flatnonzero(np.asarray(mask, bool))
    state = np.zeros(len(mask), np.uint8)
    if not len(ids):
        return state
    order = np.lexsort((-np.asarray(tie)[ids], -np.asarray(score)[ids]))
    a = max(1, int(np.ceil(.05 * len(ids))))
    b = max(a, int(np.ceil(.20 * len(ids))))
    state[ids[order[:a]]] = 2
    state[ids[order[a:b]]] = 1
    return state


def live_bands(hybrid_score) -> np.ndarray:
    """Nhóm tuyến như `run_hourly.py` dùng: điểm đã cộng lịch sử ngập, xếp trên mọi tuyến."""
    score = np.asarray(hybrid_score, np.float32)
    return route_bands(score, score, np.ones(len(score), bool))


def rank_order(score) -> np.ndarray:
    """Vị trí của từng tuyến trong đúng thứ tự `live_bands` dùng để xếp nhóm (0 là điểm cao nhất).

    Nhóm A là vị trí dưới ceil(5% số tuyến), nhóm B là tới ceil(20%). Ghi chú của tác giả web, không có trong repo mô hình.
    """
    score = np.asarray(score, np.float32)
    order = np.lexsort((-score, -score))
    position = np.empty(len(score), np.int32)
    position[order] = np.arange(len(score), dtype=np.int32)
    return position


def extent_counts(n: int, extent: tuple[float, float]) -> tuple[int, int]:
    """Số tuyến đầu bảng tô đỏ và số tuyến đầu bảng có màu, với `extent` = (phần tô đỏ, phần có màu), làm tròn lên như `route_bands`."""
    red, coloured = (int(np.ceil(q * n - 1e-9)) if q > 0 else 0 for q in extent)
    return red, max(red, coloured)


def extent_levels(position: np.ndarray, extent: tuple[float, float]) -> np.ndarray:
    """Mức của từng tuyến khi tô phần đầu bảng xếp hạng: đầu bảng cao, phần kế tiếp vừa. (0,05; 0,20) cho đúng nhóm A cao, B vừa."""
    position = np.asarray(position)
    red, coloured = extent_counts(len(position), extent)
    return np.where(position < red, HIGH, np.where(position < coloured, MEDIUM, LOW)).astype(np.uint8)


def day_state(trigger: float, t_watch: float, t_alert: float) -> int:
    """0 yên, 1 cảnh giác, 2 báo động."""
    if trigger < t_watch:
        return QUIET
    return WATCH if trigger < t_alert else ALERT


def cause_levels(bands: np.ndarray, state) -> np.ndarray:
    """Mức do một nguyên nhân: báo động thì nhóm A lên cao và nhóm B lên vừa; cảnh giác thì chỉ nhóm A lên vừa.

    `state` là một trạng thái chung cho cả thành phố, hoặc một mảng trạng thái riêng của từng tuyến
    (khi trạm mưa gần tuyến nâng trạng thái lên, ghi chú 11, QĐ4).
    """
    bands = np.asarray(bands)
    state = np.broadcast_to(np.asarray(state), bands.shape)
    on_alert = np.where(bands == 2, HIGH, np.where(bands == 1, MEDIUM, LOW))
    on_watch = np.where(bands == 2, MEDIUM, LOW)
    return np.where(state == ALERT, on_alert, np.where(state == WATCH, on_watch, LOW)).astype(np.uint8)


def route_levels(bands_rain, bands_tide, state_rain, state_tide) -> np.ndarray:
    """Mức của từng tuyến (0 thấp, 1 vừa, 2 cao): lấy mức lớn hơn giữa mưa và triều."""
    return np.maximum(cause_levels(bands_rain, state_rain), cause_levels(bands_tide, state_tide))
