"""Đối chiếu thuật toán tìm đường của nhóm với Goong (spec 05, mục 5).

    python -m floodrisk.api.routecheck hcm --pairs 60 --vehicle bike

Chọn ngẫu nhiên các cặp điểm cách nhau 3 tới 15 km, lấy lộ trình nhanh nhất của Goong và của ta, rồi ghi
`reports/route_check_{thành phố}_{xe}.md`: tỉ lệ khoảng cách, tỉ lệ thời gian, và mức trùng của hai đường đi.

Goong chỉ là một mốc tham chiếu, không phải sự thật: không ai biết thời gian của Goong có tính giao thông hay không,
nên kết quả chỉ cho biết bảng tốc độ `SPEEDS_KMH` có hợp lý không. Báo cáo ghi giờ chạy để biết đó là lúc đường vắng
hay đông. Hệ số co giãn tốc độ được gợi ý trong báo cáo; sửa bảng tốc độ là việc làm tay.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from shapely.geometry import LineString

from floodrisk import config
from floodrisk.api.goong import Goong, GoongError, decode_polyline
from floodrisk.api.graphroute import RoadGraph, RouteParams

VN = timezone(timedelta(hours=7))
BUFFER_M = 30.0  # hai đường coi là trùng nhau ở chỗ cách nhau không quá 30 m


def sample_pairs(graph: RoadGraph, vehicle: str, count: int, seed: int = 0,
                 min_m: float = 3000.0, max_m: float = 15000.0) -> list[tuple[int, int]]:
    """Các cặp nút ngẫu nhiên (cố định theo hạt giống) cách nhau min_m tới max_m theo đường chim bay."""
    graph.snap(graph.node_lon[0], graph.node_lat[0], vehicle)  # dựng chỉ mục thành phần liên thông chính
    _, usable = graph._snap[vehicle]
    rng = np.random.default_rng(seed)
    xy = graph.project(graph.node_lon[usable], graph.node_lat[usable])
    pairs: list[tuple[int, int]] = []
    for _ in range(count * 200):
        i, j = rng.choice(len(usable), 2, replace=False)
        if min_m <= float(np.hypot(*(xy[i] - xy[j]))) <= max_m:
            pairs.append((int(usable[i]), int(usable[j])))
            if len(pairs) == count:
                break
    return pairs


def _line(graph: RoadGraph, coords) -> LineString:
    arr = np.asarray(coords, dtype=float)
    return LineString(graph.project(arr[:, 0], arr[:, 1]))


def overlap(a: LineString, b: LineString, tol: float = BUFFER_M) -> float:
    """Trung bình hai chiều: phần của a nằm trong `tol` mét quanh b, và ngược lại."""
    if a.length == 0 or b.length == 0:
        return 0.0
    return 0.5 * (a.intersection(b.buffer(tol)).length / a.length + b.intersection(a.buffer(tol)).length / b.length)


def compare(graph: RoadGraph, goong: Goong, pairs: list[tuple[int, int]], vehicle: str, pause_s: float = 0.12) -> list[dict]:
    rows = []
    for a, b in pairs:
        try:
            theirs = goong.directions((graph.node_lat[a], graph.node_lon[a]), (graph.node_lat[b], graph.node_lon[b]),
                                      vehicle, alternatives=False)
        except GoongError:
            continue
        mine = graph.find_routes(a, b, vehicle, RouteParams(max_routes=1))
        if not theirs or not mine:
            continue
        their_line = _line(graph, decode_polyline(theirs[0]["polyline"]))
        my_line = _line(graph, graph.geometry(mine[0]))
        rows.append({
            "a": a, "b": b,
            "distance_ratio": mine[0].distance_m / theirs[0]["distance_m"],
            "time_ratio": mine[0].duration_s / theirs[0]["duration_s"],
            "overlap": overlap(their_line, my_line),
            "goong_m": theirs[0]["distance_m"], "goong_s": theirs[0]["duration_s"],
        })
        time.sleep(pause_s)
    return rows


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    dist = np.array([r["distance_ratio"] for r in rows])
    tim = np.array([r["time_ratio"] for r in rows])
    ov = np.array([r["overlap"] for r in rows])
    return {
        "n": len(rows),
        "distance_median": float(np.median(dist)), "distance_p10": float(np.percentile(dist, 10)),
        "distance_p90": float(np.percentile(dist, 90)),
        "time_median": float(np.median(tim)), "time_p10": float(np.percentile(tim, 10)),
        "time_p90": float(np.percentile(tim, 90)),
        "overlap_mean": float(ov.mean()), "overlap_median": float(np.median(ov)),
        "overlap_below_half": int((ov < 0.5).sum()), "overlap_above_90": int((ov >= 0.9).sum()),
        "speed_scale": float(np.median(tim)),  # nhân tốc độ với số này thì thời gian của ta khớp Goong ở trung vị
    }


def write_report(path: Path, city: str, vehicle: str, summary: dict, rows: list[dict], when: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if summary["n"] == 0:
        path.write_text(f"# Đối chiếu với Goong: {city}, {vehicle}\n\nKhông có cặp điểm nào so sánh được.\n", encoding="utf-8")
        return
    s = summary
    worst = sorted(rows, key=lambda r: r["overlap"])[:5]
    lines = [
        f"# Đối chiếu thuật toán tìm đường với Goong: {config.CITIES[city].name}, {vehicle}",
        "",
        f"Chạy lúc {when.strftime('%H:%M %A %d/%m/%Y')} (giờ Việt Nam), {s['n']} cặp điểm cách nhau 3–15 km.",
        "",
        "Goong là mốc tham chiếu, không phải sự thật. Giờ chạy cho biết đường lúc đó vắng hay đông.",
        "",
        "| Chỉ số | Kết quả |",
        "|---|---|",
        f"| Chiều dài ta / Goong | trung vị {s['distance_median']:.3f} (p10–p90: {s['distance_p10']:.3f}–{s['distance_p90']:.3f}) |",
        f"| Thời gian ta / Goong | trung vị {s['time_median']:.3f} (p10–p90: {s['time_p10']:.3f}–{s['time_p90']:.3f}) |",
        f"| Mức trùng của hai đường (trong {BUFFER_M:.0f} m) | trung bình {s['overlap_mean']:.3f}, trung vị {s['overlap_median']:.3f} |",
        f"| Số cặp trùng dưới 50% / từ 90% | {s['overlap_below_half']} / {s['overlap_above_90']} |",
        "",
        f"**Gợi ý:** nhân mọi tốc độ trong `SPEEDS_KMH[\"{vehicle}\"]` với {1 / s['speed_scale']:.3f} thì thời gian của ta khớp Goong ở trung vị "
        "(tỉ lệ thời gian trên 1 nghĩa là ta ước lâu hơn Goong, dưới 1 nghĩa là nhanh hơn).",
        "",
        "## Năm cặp ít trùng nhất (để mở trên bản đồ xem vì sao)",
        "",
        "| Mức trùng | Chiều dài ta / Goong | Thời gian ta / Goong | Từ | Tới |",
        "|---|---|---|---|---|",
    ]
    return_rows = []
    for r in worst:
        return_rows.append(f"| {r['overlap']:.2f} | {r['distance_ratio']:.2f} | {r['time_ratio']:.2f} | nút {r['a']} | nút {r['b']} |")
    path.write_text("\n".join(lines + return_rows) + "\n", encoding="utf-8")


def _load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("city", choices=list(config.CITIES))
    parser.add_argument("--pairs", type=int, default=60)
    parser.add_argument("--vehicle", choices=["bike", "car"], default="bike")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    _load_env_file()
    key = os.environ.get("GOONG_API_KEY", "")
    if not key:
        print("Thiếu GOONG_API_KEY (đặt trong .env hoặc biến môi trường)")
        return 1
    graph = RoadGraph.load(args.city)
    pairs = sample_pairs(graph, args.vehicle, args.pairs, args.seed)
    print(f"Đối chiếu {len(pairs)} cặp điểm với Goong…")
    rows = compare(graph, Goong(key), pairs, args.vehicle)
    summary = summarize(rows)
    out = Path("reports") / f"route_check_{args.city}_{args.vehicle}.md"
    write_report(out, args.city, args.vehicle, summary, rows, datetime.now(VN))
    print(f"Đã ghi {out}")
    if summary["n"]:
        print(f"  khoảng cách {summary['distance_median']:.3f} | thời gian {summary['time_median']:.3f} | trùng {summary['overlap_mean']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
