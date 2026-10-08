"""Mạng đường của ta có ngược chiều với Goong ở đâu không.

    python tools/so_chieu_duong_voi_goong.py [--pairs 20] [--vehicle bike]

Lấy lộ trình của Goong cho các cặp điểm ngẫu nhiên trong nội thành TP.HCM, dò theo từng đoạn nó đi qua trên mạng đường
của ta, và đếm những đoạn Goong đi theo chiều mà mạng của ta chỉ cho đi chiều ngược lại. Chỗ lệch nghĩa là dữ liệu
OpenStreetMap của ta và dữ liệu của Goong không thống nhất về chiều của con đường đó.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from floodrisk.api.goong import Goong, GoongError, decode_polyline
from floodrisk.api.graphroute import RoadGraph

ROOT = Path(__file__).resolve().parents[1]
CORE = (106.64, 10.74, 106.74, 10.83)  # tây, nam, đông, bắc: vùng nội thành nhiều đường một chiều
SNAP_M = 12.0
STEP_M = 8.0


def env_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("GOONG_API_KEY="):
            return line.split("=", 1)[1].strip()
    return os.environ.get("GOONG_API_KEY", "")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pairs", type=int, default=20)
    parser.add_argument("--vehicle", default="bike")
    args = parser.parse_args()

    graph = RoadGraph.load("hcm")
    xy = graph.project(graph.node_lon, graph.node_lat)
    tree = cKDTree(xy)
    forward = set(zip(graph.u.tolist(), graph.v.tolist()))
    name_of = {(int(u), int(v)): n for u, v, n in zip(graph.u, graph.v, graph.names)}
    goong = Goong(env_key())
    rng = np.random.default_rng(8)
    w, s, e, n = CORE
    agree = against = 0
    wrong_streets: Counter = Counter()
    done = 0
    while done < args.pairs:
        o = (float(rng.uniform(s, n)), float(rng.uniform(w, e)))
        d = (float(rng.uniform(s, n)), float(rng.uniform(w, e)))
        try:
            routes = goong.directions(o, d, vehicle=args.vehicle, alternatives=False)
        except GoongError as exc:
            print("Goong lỗi, chờ rồi thử lại:", exc)
            time.sleep(5)
            continue
        time.sleep(1.5)
        if not routes:
            continue
        done += 1
        line = routes[0]["geometry"] if isinstance(routes[0].get("geometry"), list) else decode_polyline(routes[0]["polyline"])
        pts = graph.project(np.array([p[0] for p in line]), np.array([p[1] for p in line]))  # polyline là (kinh độ, vĩ độ)
        dense = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            k = max(1, int(np.hypot(*(b - a)) // STEP_M))
            dense += [a + (b - a) * (i / k) for i in range(1, k + 1)]
        dist, idx = tree.query(np.array(dense))
        nodes = [int(i) for i, m in zip(idx, dist) if m <= SNAP_M]
        nodes = [x for i, x in enumerate(nodes) if i == 0 or x != nodes[i - 1]]
        for a, b in zip(nodes[:-1], nodes[1:]):
            if (a, b) in forward:
                agree += 1
            elif (b, a) in forward:
                against += 1
                wrong_streets[name_of.get((b, a)) or "Đường không tên"] += 1
    total = agree + against
    print(f"{done} lộ trình của Goong ({args.vehicle}); {total} đoạn dò được trên mạng của ta")
    print(f"Goong đi ngược chiều mạng của ta ở {against} đoạn ({against / max(1, total):.1%})")
    for name, count in wrong_streets.most_common(15):
        print(f"   {name}: {count} đoạn")


if __name__ == "__main__":
    main()
