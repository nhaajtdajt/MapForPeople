"""Thêm thứ hạng triều của từng tuyến vào bảng tuyến (cột tide_order) và lớp bản đồ (thuộc tính pt).

Mức do triều giờ tô theo bậc mực nước Phú An (src/floodrisk/live/local.py, TIDE_STEPS): triều càng cao càng tô nhiều tuyến
đầu bảng xếp hạng triều. Bảng xếp hạng là đúng thứ tự dùng để chia nhóm A, B (điểm S_hyb_tide của Mô hình 1), nên vị trí
dưới 5% là nhóm A, dưới 20% là nhóm B như cũ. tools/dung_lop_mo_hinh.py cũng ghi hai thứ này khi dựng lại từ đầu.

    python tools/them_thu_hang_trieu.py
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from floodrisk import config  # noqa: E402
from floodrisk.model.levels import rank_order  # noqa: E402


def main(city: str = "hcm") -> None:
    slug = config.MODEL_CITY[city]
    scores = pd.read_parquet(config.model_dir() / config.MODEL_VERSION / slug / "route_susceptibility.parquet", columns=["route_id", "S_hyb_tide"])
    table = pd.read_parquet(config.route_table_path(city))
    if not (scores.route_id.to_numpy() == table.route_id.to_numpy()).all():
        sys.exit("Bảng điểm và bảng tuyến không cùng thứ tự tuyến")
    order = rank_order(scores.S_hyb_tide.to_numpy())
    n = len(order)
    a, b = int(np.ceil(.05 * n)), int(np.ceil(.20 * n))
    band = np.where(order < a, 2, np.where(order < b, 1, 0))
    if not (band == table.band_tide.to_numpy()).all():
        sys.exit("Thứ hạng không khớp nhóm triều đang có")
    table["tide_order"] = order
    table.to_parquet(config.route_table_path(city), index=False, compression="zstd")

    path = config.risk_layer_path(city)
    layer = json.loads(gzip.decompress(path.read_bytes()))
    for f in layer["features"]:
        f["properties"]["pt"] = int(order[f["id"]])
    text = json.dumps(layer, ensure_ascii=False, separators=(",", ":"))
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as packed:
        packed.write(text.encode("utf-8"))
    print(f"{city}: {n} tuyến có thứ hạng triều; lớp bản đồ {len(layer['features'])} tuyến, {path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(*sys.argv[1:])
