"""Cổng duy nhất từ phần web sang mã của người dữ liệu và người AI (spec 01, mục 2.2).

Mức nguy cơ (`CityModel`) là mô hình thật, đã nằm trong repo này (ghi chú 11, QĐ1): không có bản giả, thiếu là lỗi.

Các phần còn lại được chọn riêng lúc nạp module:
- Nhập được module thật thì dùng bản thật.
- Thiếu một module có tên bắt đầu bằng `floodrisk.` (chưa làm tới) thì dùng bản giả và ghi cảnh báo.
- Mọi lỗi khác được ném ra nguyên vẹn, để lỗi trong module thật không bị giấu tới buổi trình diễn.

Không file nào khác trong `api/` được nhập từ `floodrisk.model`, `floodrisk.data` hay `floodrisk.jobs`.
"""
from __future__ import annotations

import importlib
import logging

from floodrisk.api import fakes
from floodrisk.model.live import CityModel, Snapshot, current_hour  # noqa: F401  (xuất lại cho phần web)
from floodrisk.model.levels import LEVEL_NAMES, STATE_NAMES  # noqa: F401

log = logging.getLogger(__name__)

# phần -> (module thật, các tên cần lấy, tên trong fakes khi thay thế)
PARTS: dict[str, tuple[str, dict[str, str]]] = {
    "evidence": ("floodrisk.model.evidence", {"Report": "Report", "EvidenceResult": "EvidenceResult",
                                              "apply_evidence": "apply_evidence"}),
    "scenarios": ("floodrisk.model.scenarios", {"make_synthetic": "make_synthetic",
                                                "make_past_moment": "make_past_moment"}),
}

_status: dict[str, str] = {}
_objects: dict[str, object] = {}


def _is_ours(exc: ModuleNotFoundError) -> bool:
    return exc.name == "floodrisk" or (exc.name or "").startswith("floodrisk.")


def _load(part: str) -> None:
    module_name, names = PARTS[part]
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if not _is_ours(exc):
            raise
        log.warning("Chưa có %s (thiếu module %s); phần '%s' dùng bản giả", module_name, exc.name, part)
        _status[part] = "fake"
        for exported, real_name in names.items():
            _objects[exported] = getattr(fakes, real_name)
        return
    for exported, real_name in names.items():
        if not hasattr(module, real_name):
            raise RuntimeError(f"{module_name} thiếu '{real_name}' mà hợp đồng yêu cầu (QĐKT mục 6)")
        _objects[exported] = getattr(module, real_name)
    _status[part] = "real"


for _part in PARTS:
    _load(_part)

Report = _objects["Report"]
EvidenceResult = _objects["EvidenceResult"]
apply_evidence = _objects["apply_evidence"]
make_synthetic = _objects["make_synthetic"]
make_past_moment = _objects["make_past_moment"]


def status() -> dict[str, str]:
    """Phần nào đang là bản thật (`real`) hay bản giả (`fake`)."""
    return {"risk": "real", **_status}
