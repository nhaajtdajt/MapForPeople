from __future__ import annotations

from dataclasses import dataclass, field

from floodrisk import config
from floodrisk.api.goong import Goong


@dataclass
class Context:
    goong: Goong
    last_refresh: str | None = None
    last_error: str | None = None
    traffic: dict = field(default_factory=dict)

    def traffic_status(self) -> dict:
        """Nguồn giao thông của từng thành phố. Mặc định là bảng điển hình cho tới khi có TomTom (spec 09)."""
        return {key: self.traffic.get(key, {"source": "typical", "observed_at": None}) for key in config.CITIES}
