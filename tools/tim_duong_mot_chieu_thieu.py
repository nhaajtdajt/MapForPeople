"""Tìm những đoạn đường mà mạng của ta cho đi hai chiều nhưng Goong chỉ cho đi một chiều.

    python tools/tim_duong_mot_chieu_thieu.py [--edges 40] [--vehicle bike]

Lấy ngẫu nhiên các đoạn đường hai chiều trong nội thành TP.HCM (theo mạng của ta), rồi hỏi Goong đường đi dọc đoạn đó
theo cả hai chiều. Nếu một chiều Goong đi thẳng còn chiều kia Goong phải đi vòng xa, thì Goong coi đoạn đó là một chiều:
bộ tìm đường của ta sẽ chỉ người dùng đi ngược chiều ở đó.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from floodrisk.api.goong import Goong, GoongError
from floodrisk.api.graphroute import RoadGraph

ROOT = Path(__file__).resolve().parents[1]
CORE = (106.66, 10.75, 106.72, 10.81)  # tây, nam, đông, bắc
CLASSES = {"primary", "secondary", "tertiary", "residential"}
DETOUR = 2.5  # Goong đi dài hơn chừng này lần so với chiều kia thì coi là bị cấm chiều đó
MIN_EXTRA_M = 200.0


def env_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("GOONG_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def ask(goong: Goong, a, b, vehicle: str) -> float | None:
    for _ in range(3):
        try:
            routes = goong.directions(a, b, vehicle=vehicle, alternatives=False)
            time.sleep(1.3)
            return float(routes[0]["distance_m"]) if routes else None
        except GoongError:
            time.sleep(6)
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--edges", type=int, default=40)
    parser.add_argument("--vehicle", default="bike")
    args = parser.parse_args()

    graph = RoadGraph.load("hcm")
    w, s, e, n = CORE
    forward = set(zip(graph.u.tolist(), graph.v.tolist()))
    lon, lat = graph.node_lon, graph.node_lat
    inside = (lon[graph.u] > w) & (lon[graph.u] < e) & (lat[graph.u] > s) & (lat[graph.u] < n)
    two_way = np.array([(v, u) in forward for u, v in zip(graph.u.tolist(), graph.v.tolist())])
    named = np.array([bool(x) and not str(x).startswith("Hẻm") for x in graph.names])
    klass = np.array([str(h) in CLASSES for h in graph.highway])
    pool = np.flatnonzero(inside & two_way & named & klass & (graph.length_m > 120) & (graph.length_m < 400) & (graph.u < graph.v))
    picked = np.random.default_rng(3).choice(pool, size=min(args.edges, len(pool)), replace=False)
    goong = Goong(env_key())
    one_way, checked = [], 0
    for edge in picked:
        coords = graph.edge_coords(int(edge))
        a = coords[max(1, len(coords) // 5)] if len(coords) > 4 else coords[0]
        b = coords[-max(2, len(coords) // 5)] if len(coords) > 4 else coords[-1]
        pa, pb = (float(a[1]), float(a[0])), (float(b[1]), float(b[0]))
        there, back = ask(goong, pa, pb, args.vehicle), ask(goong, pb, pa, args.vehicle)
        if there is None or back is None:
            continue
        checked += 1
        short, long = min(there, back), max(there, back)
        if long > DETOUR * max(short, 30.0) and long - short > MIN_EXTRA_M:
            one_way.append((graph.names[edge], str(graph.highway[edge]), round(short), round(long), pa))
    print(f"{checked} đoạn hai chiều (theo mạng của ta) đã hỏi Goong, xe {args.vehicle}")
    print(f"Goong coi là một chiều: {len(one_way)} đoạn ({len(one_way) / max(1, checked):.0%})")
    for name, klass_name, short, long, at in one_way:
        print(f"   {name} ({klass_name}): chiều thuận {short} m, chiều ngược Goong phải đi {long} m | tại {at[0]:.5f}, {at[1]:.5f}")


if __name__ == "__main__":
    main()
