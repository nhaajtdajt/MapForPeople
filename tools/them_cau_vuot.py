"""Đánh dấu các tuyến là cầu, cầu vượt (cột elevated trong bảng tuyến, thuộc tính ev trong lớp bản đồ): không bao giờ tô ngập.

Mặt cầu không ngập do mưa hay triều, nhưng Mô hình 1 xếp cả cầu vượt Hàng Xanh, cầu Điện Biên Phủ... vào nhóm dễ ngập, vì
điểm ngập ghi nhận dưới gầm cầu được gắn vào đoạn đường gần nhất là đoạn cầu ngay phía trên (16 cầu có "lịch sử ngập").
Tuyến được coi là cầu khi ít nhất một nửa chiều dài là đường OSM gắn bridge=*. Đường dưới đất, vòng xoay, chân cầu giữ nguyên.

    python tools/them_cau_vuot.py
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

BRIDGE_SHARE = 0.5


def main(city: str = "hcm") -> None:
    slug = config.MODEL_CITY[city]
    source = ROOT / "data" / "raw" / "model_build" / f"{slug}_routes_linux.parquet"
    built = pd.read_parquet(source, columns=["name", "length_m", "bridge_frac"])
    table = pd.read_parquet(config.route_table_path(city))
    # Ghép theo dòng như tools/dung_lop_mo_hinh.py (mã tuyến không tên khác giữa hai lần dựng); kiểm bằng tên và chiều dài.
    if len(built) != len(table) or not ((built.name.fillna("") == table.name.fillna("")).all() and (abs(built.length_m - table.length_m) < 1).all()):
        sys.exit(f"{source.name} không khớp bảng tuyến theo dòng")
    table["elevated"] = built.bridge_frac.fillna(0).to_numpy() >= BRIDGE_SHARE
    table.to_parquet(config.route_table_path(city), index=False, compression="zstd")

    path = config.risk_layer_path(city)
    layer = json.loads(gzip.decompress(path.read_bytes()))
    elevated = table.elevated.to_numpy()
    marked = 0
    for feature in layer["features"]:
        props = feature["properties"]
        if elevated[feature["id"]]:
            props["ev"] = 1
            marked += 1
        else:
            props.pop("ev", None)
    text = json.dumps(layer, ensure_ascii=False, separators=(",", ":"))
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as packed:
        packed.write(text.encode("utf-8"))
    print(f"{city}: {int(elevated.sum())} tuyến là cầu (từ {BRIDGE_SHARE:.0%} chiều dài); {marked} trong lớp bản đồ; "
          f"trong đó nhóm A/B mưa {int((elevated & (table.band_rain.to_numpy() > 0)).sum())}, triều {int((elevated & (table.band_tide.to_numpy() > 0)).sum())}")


if __name__ == "__main__":
    main(*sys.argv[1:])
