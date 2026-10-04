"""Chạy máy chủ ở chế độ phát triển, một lệnh:

    python -m floodrisk.api.dev

Mặc định dùng dữ liệu mẫu (`data/sample`, tự sinh nếu chưa có), tắt tác vụ nền và bật bàn thử. Muốn chạy trên dữ liệu
thật hoặc đổi cổng thì đặt biến môi trường trong cửa sổ dòng lệnh trước khi chạy (FLOODRISK_DATA, REFRESH_MINUTES,
FLOODRISK_TEST_TOOLS, PORT); giá trị đặt ở đó thắng giá trị trong `.env`. Khóa Goong và TomTom đọc từ `.env`.
"""
from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from floodrisk.api.devdata import make_dev_data


def main() -> None:
    os.environ.setdefault("FLOODRISK_DATA", "data/sample")
    os.environ.setdefault("REFRESH_MINUTES", "0")
    os.environ.setdefault("FLOODRISK_TEST_TOOLS", "1")

    root = Path(os.environ["FLOODRISK_DATA"])
    if root.name == "sample" and not (root / "processed" / "SAMPLE").exists():
        make_dev_data(root)

    uvicorn.run(
        "floodrisk.api.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "8000")),
        env_file=".env",
        log_level="info",
    )


if __name__ == "__main__":
    main()
