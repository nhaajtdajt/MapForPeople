from __future__ import annotations

import os
from pathlib import Path

from floodrisk.config import data_dir


def goong_api_key() -> str:
    return os.environ.get("GOONG_API_KEY", "")


def refresh_minutes() -> int:
    return int(os.environ.get("REFRESH_MINUTES", "60"))


def test_tools_enabled() -> bool:
    return os.environ.get("FLOODRISK_TEST_TOOLS", "") == "1"


def risk_push_token() -> str:
    """Mã cho phép một máy khác đẩy bản tính của mô hình lên máy chủ này. Rỗng thì máy chủ không nhận."""
    return os.environ.get("RISK_PUSH_TOKEN", "")


def db_path() -> Path:
    return data_dir() / "reports.sqlite"


def web_dist() -> Path:
    return Path(os.environ.get("FLOODRISK_WEB_DIST", "web/dist"))
