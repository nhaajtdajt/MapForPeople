"""Bảng kê dữ liệu: file nào đã có, của ai, thật hay mẫu.

    python -m floodrisk.api.inventory

Ghi `data/README.md`. Quét hai nơi, tách bạch:
  data/processed/         DỮ LIỆU THẬT (người dữ liệu, người AI giao)
  data/sample/processed/  DỮ LIỆU MẪU, giả, sinh bằng `python -m floodrisk.api.devdata data/sample`

Chạy lại mỗi khi có file mới. File README này là thứ duy nhất trong `data/` được đưa vào git.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pyarrow.parquet as pq

from floodrisk import config

DATA = "Dữ liệu"
AI = "AI"

# (đường dẫn dưới processed/, người giao). {city} được thay bằng mã thành phố.
PER_CITY: list[tuple[str, str]] = [
    ("{city}/units.parquet", DATA),
    ("{city}/observations.parquet", DATA),
    ("{city}/obs_units.parquet", DATA),
    ("{city}/graph_nodes.parquet", DATA),
    ("{city}/graph_edges.parquet", DATA),
    ("{city}/edge_units.parquet", DATA),
    ("{city}/rain_cells.parquet", DATA),
    ("{city}/rain_daily.parquet", DATA),
    ("{city}/scores.parquet", AI),
    ("{city}/risk.parquet", AI),
    ("{city}/model/trigger.json", AI),
    ("{city}/replay/index.json", AI),
]
GLOBAL: list[tuple[str, str]] = [
    ("model_choice.json", AI),
    ("tide_daily.parquet", AI),
    ("tide_coef.joblib", AI),
]


def _describe(path: Path) -> tuple[str, str, str]:
    """(số dòng, dung lượng, ngày sửa) của một file; ba dấu gạch ngang nếu thiếu."""
    if not path.exists():
        return "—", "—", "—"
    size = f"{path.stat().st_size / 1_000_000:.1f} MB"
    day = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y")
    rows = ""
    if path.suffix == ".parquet":
        rows = f"{pq.ParquetFile(path).metadata.num_rows:,}".replace(",", ".")
    elif path.name == "index.json":
        rows = f"{len(json.loads(path.read_text(encoding='utf-8')))} kịch bản"
    return rows or "", size, day


def _table(base: Path) -> list[str]:
    lines: list[str] = []
    for city in config.CITIES:
        folder = base / "processed" / city
        lines += [f"### {config.CITIES[city].name} (`{city}`)", "",
                  "| File | Ai giao | Trạng thái | Số dòng | Dung lượng | Sửa lần cuối |", "|---|---|---|---|---|---|"]
        present = 0
        for rel, owner in PER_CITY:
            path = base / "processed" / rel.format(city=city)
            rows, size, day = _describe(path)
            present += path.exists()
            lines.append(f"| `{rel.format(city=city)}` | {owner} | {'có' if path.exists() else '**thiếu**'} | {rows} | {size} | {day} |")
        lines += ["", f"Có {present}/{len(PER_CITY)} file." if folder.exists() else "Chưa có thư mục này.", ""]
    lines += ["### Dùng chung cho mọi thành phố", "",
              "| File | Ai giao | Trạng thái | Số dòng | Dung lượng | Sửa lần cuối |", "|---|---|---|---|---|---|"]
    for rel, owner in GLOBAL:
        path = base / "processed" / rel
        rows, size, day = _describe(path)
        lines.append(f"| `{rel}` | {owner} | {'có' if path.exists() else '**thiếu**'} | {rows} | {size} | {day} |")
    return lines + [""]


def build(real_root: Path, sample_root: Path) -> str:
    out = [
        "# Dữ liệu của dự án",
        "",
        "Tệp này được sinh tự động bởi `python -m floodrisk.api.inventory`. Đừng sửa tay; chạy lại lệnh khi có file mới.",
        "",
        "## Đọc cho đúng: thật hay mẫu",
        "",
        "| Thư mục | Là gì | Dùng để |",
        "|---|---|---|",
        "| `data/processed/` | **DỮ LIỆU THẬT** do người dữ liệu và người AI giao | Chạy sản phẩm thật, đo, trình diễn |",
        "| `data/sample/processed/` | **DỮ LIỆU MẪU, GIẢ.** Tám đường tưởng tượng mỗi thành phố, sinh bằng lệnh | Phát triển khi file thật chưa đến. Không dùng làm bằng chứng cho bất cứ điều gì |",
        "",
        "Hai nơi không bao giờ trộn file với nhau. Máy chủ chọn nơi nào theo biến `FLOODRISK_DATA` "
        "(`data` là thật, `data/sample` là mẫu). `/api/health` ghi `data: real` hay `data: sample`.",
        "",
        f"Cập nhật lúc {datetime.now().strftime('%H:%M %d/%m/%Y')}.",
        "",
        "## Dữ liệu thật (`data/processed/`)",
        "",
        *_table(real_root),
        "## Dữ liệu mẫu, giả (`data/sample/processed/`)",
        "",
        "> Mọi file dưới đây là giả. Chúng chỉ tồn tại để phần web chạy được khi file thật chưa đến.",
        "",
        *_table(sample_root),
    ]
    return "\n".join(out)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    text = build(root, root / "sample")
    (root / "README.md").write_text(text, encoding="utf-8")
    print(f"Đã ghi {root / 'README.md'}")


if __name__ == "__main__":
    main()
