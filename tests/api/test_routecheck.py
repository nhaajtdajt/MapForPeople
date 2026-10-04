from datetime import datetime

import httpx
import numpy as np
import pytest
from shapely.geometry import LineString

from floodrisk.api import routecheck
from floodrisk.api.goong import Goong, decode_polyline
from floodrisk.api.graphroute import RoadGraph, RouteParams


def encode_polyline(points, precision=5):
    """Bộ mã hóa polyline (chỉ để dựng dữ liệu kiểm thử)."""
    out, prev_lat, prev_lon = [], 0, 0
    for lon, lat in points:
        for value, previous in ((round(lat * 10**precision), prev_lat), (round(lon * 10**precision), prev_lon)):
            delta = value - previous
            delta = ~(delta << 1) if delta < 0 else delta << 1
            while delta >= 0x20:
                out.append(chr((0x20 | (delta & 0x1F)) + 63))
                delta >>= 5
            out.append(chr(delta + 63))
        prev_lat, prev_lon = round(lat * 10**precision), round(lon * 10**precision)
    return "".join(out)


def test_polyline_round_trip_and_known_value():
    # Ví dụ trong tài liệu của Google: (38.5, -120.2), (40.7, -120.95), (43.252, -126.453)
    assert decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@") == [(-120.2, 38.5), (-120.95, 40.7), (-126.453, 43.252)]
    points = [(106.69812, 10.77251), (106.70011, 10.77904), (106.71, 10.8)]
    assert decode_polyline(encode_polyline(points)) == points


def test_overlap_is_symmetric_and_respects_the_tolerance():
    a = LineString([(0, 0), (1000, 0)])
    assert routecheck.overlap(a, a) == 1.0
    assert routecheck.overlap(a, LineString([(0, 20), (1000, 20)])) == 1.0  # lệch 20 m: vẫn trùng
    assert routecheck.overlap(a, LineString([(0, 80), (1000, 80)])) == 0.0  # lệch 80 m: khác đường
    half = LineString([(0, 0), (500, 0)])
    # vùng đệm 30 m kéo dài thêm 30 m ở đầu mút: phần trùng của a là 530/1000, của half là 100%
    assert routecheck.overlap(a, half) == pytest.approx((0.53 + 1.0) / 2)
    assert routecheck.overlap(half, a) == routecheck.overlap(a, half)


def make_fake_goong(graph: RoadGraph, scale: float):
    """Goong giả đi đúng đường của ta, với thời gian bằng `scale` lần thời gian của ta."""
    def handler(request):
        o_lat, o_lon = map(float, request.url.params["origin"].split(","))
        d_lat, d_lon = map(float, request.url.params["destination"].split(","))
        a, _ = graph.snap(o_lon, o_lat, "bike")
        b, _ = graph.snap(d_lon, d_lat, "bike")
        route = graph.find_routes(a, b, "bike", RouteParams(max_routes=1))[0]
        points = [tuple(p) for p in graph.geometry(route)]
        return httpx.Response(200, json={"routes": [{
            "overview_polyline": {"points": encode_polyline(points)},
            "legs": [{"distance": {"value": route.distance_m}, "duration": {"value": route.duration_s * scale}}],
        }]})
    return Goong("KEY", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_compare_against_an_identical_reference_finds_full_overlap_and_the_time_scale(data):
    graph = RoadGraph.load("hcm")
    pairs = [(0, 15), (3, 12), (5, 10)]
    rows = routecheck.compare(graph, make_fake_goong(graph, scale=1.5), pairs, "bike", pause_s=0)
    summary = routecheck.summarize(rows)
    assert summary["n"] == 3
    assert summary["overlap_mean"] > 0.99 and summary["distance_median"] == np.float64(summary["distance_median"])
    assert abs(summary["distance_median"] - 1.0) < 0.01
    assert abs(summary["time_median"] - 1 / 1.5) < 1e-6  # ta nhanh hơn "Goong" 1,5 lần
    assert abs(1 / summary["speed_scale"] - 1.5) < 1e-6  # gợi ý: nhân tốc độ với 1,5


def test_goong_errors_skip_the_pair_instead_of_failing(data):
    graph = RoadGraph.load("hcm")
    down = Goong("KEY", client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    assert routecheck.compare(graph, down, [(0, 15)], "bike", pause_s=0) == []
    assert routecheck.summarize([]) == {"n": 0}


def test_sample_pairs_are_reproducible_and_in_range(data):
    graph = RoadGraph.load("hcm")
    # lưới mẫu chỉ rộng ~600 m nên đặt khoảng cách nhỏ cho phù hợp
    first = routecheck.sample_pairs(graph, "bike", 5, seed=3, min_m=200, max_m=900)
    assert first == routecheck.sample_pairs(graph, "bike", 5, seed=3, min_m=200, max_m=900) and len(first) == 5
    assert all(a != b for a, b in first)


def test_report_is_written_in_vietnamese(data, tmp_path):
    graph = RoadGraph.load("hcm")
    rows = routecheck.compare(graph, make_fake_goong(graph, 1.0), [(0, 15), (3, 12)], "bike", pause_s=0)
    path = tmp_path / "reports" / "r.md"
    routecheck.write_report(path, "hcm", "bike", routecheck.summarize(rows), rows, datetime(2026, 10, 4, 21, 0))
    text = path.read_text(encoding="utf-8")
    assert "Đối chiếu thuật toán tìm đường với Goong" in text and "Thời gian ta / Goong" in text and "Gợi ý" in text
    empty = tmp_path / "empty.md"
    routecheck.write_report(empty, "hcm", "bike", {"n": 0}, [], datetime(2026, 10, 4))
    assert "Không có cặp điểm nào" in empty.read_text(encoding="utf-8")
