"""GET /api/route trên đồ thị mẫu (lưới 4 × 4, mỗi khúc khoảng 200 m, ở trung tâm TP.HCM)."""
from datetime import datetime

import pytest

from floodrisk import config
from floodrisk.api.devdata import make_dev_data
from floodrisk.api.graphroute import GraphError, RoadGraph

STEP = 0.0018
ORIGIN = "10.78,106.7"  # nút 00
DEST = f"{10.78 + 3 * STEP},{106.7 + 3 * STEP}"  # nút 33


def get(client, **params):
    base = {"city": "hcm", "origin": ORIGIN, "destination": DEST}
    return client.get("/api/route", params={**base, **params})


def test_route_returns_ranked_alternatives_with_steps_and_geometry(client):
    body = get(client).json()
    routes = body["routes"]
    assert len(routes) >= 2
    first = routes[0]
    assert first["kind"] == "fastest" and first["recommended"] is True and first["engine"] == "own"
    assert all(not r["recommended"] for r in routes[1:])
    assert [r["duration_s"] for r in routes] == sorted(r["duration_s"] for r in routes)
    assert 1100 < first["distance_m"] < 1300 and first["estimated"] is True
    coords = first["geometry"]["coordinates"]
    assert first["geometry"]["type"] == "LineString" and len(coords) >= 2
    assert coords[0] == [106.7, 10.78] and coords[-1] == [pytest.approx(106.7 + 3 * STEP, abs=1e-6), pytest.approx(10.78 + 3 * STEP, abs=1e-6)]
    assert first["steps"] and first["steps"][0]["turn"] == "start" and first["steps"][0]["name"].startswith("Đường Mẫu")
    assert datetime.fromisoformat(first["arrive_at"]).utcoffset().total_seconds() == 7 * 3600
    assert body["snapped"]["origin"]["distance_m"] < 5 and body["traffic"]["source"] == "none"
    assert any("ước lượng" in note for note in body["notes"])


def test_car_and_bike_both_work(client):
    assert get(client, vehicle="car").status_code == 200
    assert get(client, vehicle="bike").status_code == 200


def test_input_errors_are_vietnamese_and_precise(client):
    cases = [
        (dict(origin="abc"), 422, "vĩ độ,kinh độ"),
        (dict(destination="10.78"), 422, "vĩ độ,kinh độ"),
        (dict(origin="95,106.7"), 422, "không hợp lệ"),
        (dict(vehicle="tank"), 422, "Loại xe"),
        (dict(origin="21.03,105.85"), 422, "ngoài khu vực"),  # Hà Nội: ngoài khung TP.HCM
        (dict(origin="10.9,106.85"), 422, "không gần đường nào"),  # trong khung nhưng cách xa mạng đường mẫu
        (dict(destination=ORIGIN), 422, "quá gần"),
        (dict(city="hanoi"), 404, "không có trong hệ thống"),
    ]
    for override, status, fragment in cases:
        res = get(client, **override)
        assert res.status_code == status and fragment in res.json()["detail"], (override, res.text)


def test_unreachable_destination_is_404(client, monkeypatch):
    monkeypatch.setattr(RoadGraph, "find_routes", lambda *a, **k: [])
    res = get(client)
    assert res.status_code == 404 and "Không tìm được đường" in res.json()["detail"]


def test_city_without_a_road_network_is_404_and_recovers_when_files_arrive(client, data):
    config.graph_nodes_path("hcm").unlink()
    res = get(client)
    assert res.status_code == 404 and "chưa có mạng đường" in res.json()["detail"]
    make_dev_data(data)  # file xuất hiện: dùng được ngay, không cần khởi động lại
    assert get(client).status_code == 200


def test_graph_is_loaded_once_and_reused(client):
    get(client)
    first = client.app.state.ctx.graphs["hcm"]
    get(client)
    assert client.app.state.ctx.graphs["hcm"] is first


def test_loading_the_sample_network_names_streets_from_units(data):
    graph = RoadGraph.load("hcm")
    assert graph.n == 16 and graph.m == 48
    assert set(graph.names) == {f"Đường Mẫu Ngang {i}" for i in range(1, 5)} | {f"Đường Mẫu Dọc {i}" for i in range(1, 5)}


def test_loading_a_corrupt_network_is_reported(data):
    import pandas as pd

    nodes = pd.read_parquet(config.graph_nodes_path("hcm")).iloc[:8]  # bỏ bớt nút nhưng cạnh vẫn trỏ tới chúng
    nodes.to_parquet(config.graph_nodes_path("hcm"))
    with pytest.raises(GraphError, match="nút"):
        RoadGraph.load("hcm")
