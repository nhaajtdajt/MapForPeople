"""Mức ngập trên từng cạnh của mạng đường, để tìm đường tránh ngập theo bậc bằng chứng (ghi chú 11, QĐ5).

Bậc 1 (đang có người hoặc camera báo ngập) được thêm cùng phần báo ngập. Ở đây có hai bậc còn lại:
- bậc 2: tuyến từng có ghi nhận ngập và hôm nay đang có mức: cộng thời gian nặng;
- bậc 3: tuyến chỉ do mô hình xếp hạng: cộng thời gian nhẹ.
Các hệ số là do người làm web đặt, chưa hiệu chỉnh.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from floodrisk import config

CONFIRMED_FACTOR = 50.0  # đang có người hoặc camera báo ngập vừa trở lên: chỉ đi qua khi không còn đường nào khác
HISTORY_FACTOR = 10.0  # tuyến từng ngập, đang có mức
MODEL_HIGH_FACTOR = 2.0  # mô hình xếp mức cao, chưa từng có ghi nhận
MODEL_MEDIUM_FACTOR = 1.3  # mô hình xếp mức vừa, chưa từng có ghi nhận
MAX_SEGMENTS = 5


@dataclass(frozen=True)
class FloodView:
    edge_route: np.ndarray  # với mỗi cạnh của mạng đường: số dòng của tuyến trong bảng tuyến, -1 nếu không gắn được
    level: np.ndarray  # mức của từng tuyến lúc này: 0 thấp, 1 vừa, 2 cao
    history: np.ndarray  # tuyến từng có ghi nhận ngập
    names: np.ndarray  # tên tuyến
    confirmed: np.ndarray | None = None  # tuyến đang có báo cáo ngập vừa trở lên (bậc 1)


def edge_route_rows(city: str, route_ids: np.ndarray) -> np.ndarray | None:
    """Gắn từng cạnh của mạng đường vào dòng của tuyến chứa nó. None nếu thành phố chưa có bảng gắn."""
    path = config.processed_dir(city) / "edge_routes.parquet"
    if not path.exists():
        return None
    edge_ids = pq.read_table(config.graph_edges_path(city), columns=["edge_id"]).column("edge_id").to_numpy()
    links = pd.read_parquet(path, columns=["edge_id", "route_id", "length_m"])
    links = links.sort_values(["edge_id", "length_m"], ascending=[True, False]).drop_duplicates("edge_id")
    row_of_route = pd.Series(np.arange(len(route_ids)), index=route_ids)
    rows = row_of_route.reindex(links.route_id.to_numpy()).to_numpy()
    by_edge = pd.Series(rows, index=links.edge_id.to_numpy())
    return by_edge.reindex(edge_ids).fillna(-1).to_numpy(np.int64)


def _edge_levels(view: FloodView) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    attached = view.edge_route >= 0
    rows = np.where(attached, view.edge_route, 0)
    confirmed = attached & view.confirmed[rows] if view.confirmed is not None else np.zeros(len(rows), bool)
    return np.where(attached, view.level[rows], 0), attached & view.history[rows], confirmed


def slow_factors(view: FloodView) -> np.ndarray:
    """Hệ số làm chậm từng cạnh: 1 ở cạnh không có mức."""
    level, history, confirmed = _edge_levels(view)
    model = np.where(level == 2, MODEL_HIGH_FACTOR, np.where(level == 1, MODEL_MEDIUM_FACTOR, 1.0))
    return np.where(confirmed, CONFIRMED_FACTOR, np.where((level > 0) & history, HISTORY_FACTOR, model))


def exposure(edges: np.ndarray, length_m: np.ndarray, view: FloodView) -> dict:
    """Một lộ trình đi qua bao nhiêu mét đường đang có mức, và những tuyến nào đóng góp nhiều nhất."""
    level, history, confirmed = _edge_levels(view)
    lv, hs, cf, ln, rows = level[edges], history[edges], confirmed[edges], length_m[edges], view.edge_route[edges]
    parts = pd.DataFrame({"row": rows, "level": lv, "history": hs, "confirmed": cf, "m": ln})
    parts = parts[parts.level > 0]
    top = parts.groupby("row").agg(level=("level", "max"), history=("history", "max"), confirmed=("confirmed", "max"), m=("m", "sum")).sort_values(
        ["confirmed", "history", "level", "m"], ascending=False).head(MAX_SEGMENTS)
    return {
        "high_m": round(float(ln[lv == 2].sum())), "medium_m": round(float(ln[lv == 1].sum())),
        "history_m": round(float(ln[(lv > 0) & hs].sum())), "confirmed_m": round(float(ln[cf].sum())),
        "segments": [{"name": view.names[int(row)] or "Đường chưa có tên", "level": int(r.level),
                      "basis": "report" if r.confirmed else "history" if r.history else "model", "length_m": round(float(r.m))}
                     for row, r in top.iterrows()],
    }
