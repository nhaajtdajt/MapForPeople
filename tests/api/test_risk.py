"""Đường nối từ mô hình sang bản đồ: /api/risk, /api/risk/routes, /api/risk/points (ghi chú 11, QĐ1 và QĐ4)."""
import gzip
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from floodrisk import config
from floodrisk.model.levels import live_bands

TZ = "Asia/Ho_Chi_Minh"
RAIN = {"selected_features": ["rain_max_3h_mm", "rain_total_mm"],
        "coef": [0.02283375645176585, 0.02851568232758494], "intercept": -0.0017792662252086328}
N_ROUTES = 100


def _write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


@pytest.fixture
def model_data(data):
    """Một mô hình tí hon cho TP.HCM trong thư mục dữ liệu của kiểm thử: 100 tuyến, cùng ngưỡng với mô hình thật."""
    root = config.model_dir()
    version = root / config.MODEL_VERSION
    _write_json(root / "final_config.json", {"q_watch": 0.5093524878214044, "q_alert": 0.5395158283435458})
    _write_json(root / "combination_thresholds.json",
                {"thresholds": {"ho_chi_minh": {"tide": {"t_lo": 0.5718924778699874, "t_hi": 0.581133896112442}}}})
    _write_json(root / "m2_ho_chi_minh_tide.json", {"kind": "percentile", "climatology_q": list(np.linspace(3.0, 4.0, 201))})
    _write_json(version / "rain_trigger.json", RAIN)
    reference = pd.DataFrame({"rain_max_3h_mm": np.arange(1000) / 10, "rain_total_mm": np.arange(1000) / 10})
    for source in ("ifs", "era5"):
        (version / "cdfs").mkdir(parents=True, exist_ok=True)
        reference.to_parquet(version / "cdfs" / f"ho_chi_minh_{source}_reference.parquet")

    score = np.linspace(1.0, 0.0, N_ROUTES, dtype=np.float32)  # tuyến 0 điểm cao nhất theo mưa
    table = pd.DataFrame({
        "route_id": [f"r{i:03d}" for i in range(N_ROUTES)], "name": [f"Đường {i}" for i in range(N_ROUTES)],
        "highway_class": "residential", "length_m": 100.0, "in_universe": True,
        "band_rain": live_bands(score), "band_tide": live_bands(score[::-1].copy()),
        "history_rain": False, "history_tide": False, "history_dates_rain": 0, "history_dates_tide": 0,
    })
    table.to_parquet(config.route_table_path("hcm"), index=False)
    hours = pd.date_range(pd.Timestamp.now(tz="UTC").floor("h") - pd.Timedelta(hours=24), periods=72, freq="h")
    pd.DataFrame({"time_utc": hours, "astro_m": 3.2}).to_parquet(config.tide_hourly_path("hcm"), index=False)

    layer = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": 0, "geometry": {"type": "LineString", "coordinates": [[106.7, 10.78], [106.701, 10.78]]},
         "properties": {"id": "r000", "name": "Đường 0", "cls": "residential", "len": 100, "br": 2, "bt": 0, "hr": 0, "ht": 0}}]}
    config.risk_layer_path("hcm").write_bytes(gzip.compress(json.dumps(layer).encode("utf-8")))
    config.flood_points_path("hcm").write_text(
        "no,cause,place,n_routes,located_by,lon,lat,route_ids\n"
        "1,rain,Ngã tư thử,1,tại chỗ giao,106.7,10.78,r000\n"
        "2,tide,Điểm ngoài vùng,0,ngoài vùng mô hình,,,\n", encoding="utf-8")
    return data


def _rain(mm_last_3h: float):
    """Nguồn mưa giả: `mm_last_3h` rơi đều trong ba giờ vừa qua, còn lại khô."""
    def fetch(city, model):
        now = pd.Timestamp.now(tz=TZ).floor("h")
        series = pd.Series(0.0, index=pd.date_range(now - pd.Timedelta(hours=72), now + pd.Timedelta(hours=12), freq="h"))
        series[(series.index > now - pd.Timedelta(hours=3)) & (series.index <= now)] = mm_last_3h / 3
        return series
    return fetch


def _client(fetch):
    from floodrisk.api.main import create_app

    app = create_app()
    app.state.ctx.rain_fetch = fetch
    return TestClient(app), app.state.ctx


def test_dry_day_is_quiet_and_no_route_has_a_level(model_data):
    client, _ = _client(_rain(0.0))
    body = client.get("/api/risk", params={"city": "hcm"}).json()
    assert body["city"] == "hcm" and body["model_version"] == config.MODEL_VERSION and body["stale"] is False
    assert [h["rain"]["state"] for h in body["hours"]] == ["quiet"] * 3
    assert body["hours"][0]["tide"]["state"] == "quiet" and body["hours"][0]["tide"]["astro_m"] == 3.2
    assert body["hours"][0]["counts"] == {"high": 0, "medium": 0}
    assert body["layer"]["url"].startswith("/api/risk/routes?city=hcm&v=")


def test_watch_raises_only_band_a_and_alert_raises_both_bands(model_data):
    watch, _ = _client(_rain(80.0))  # khoảng 80% số ngày tham chiếu mưa ít hơn: cảnh giác
    hour = watch.get("/api/risk").json()["hours"][0]
    assert hour["rain"]["state"] == "watch" and hour["rain"]["max_3h_mm"] == 80.0 and hour["rain"]["total_24h_mm"] == 80.0
    assert hour["counts"] == {"high": 0, "medium": 5}  # 5% của 100 tuyến

    alert, _ = _client(_rain(99.0))
    hour = alert.get("/api/risk").json()["hours"][0]
    assert hour["rain"]["state"] == "alert" and hour["counts"] == {"high": 5, "medium": 15}
    assert 0.41 < hour["rain"]["trigger"] < 0.59


def test_a_failed_refresh_keeps_the_last_result_and_says_so(model_data):
    calls = {"fail": False}
    good = _rain(99.0)

    def fetch(city, model):
        if calls["fail"]:
            raise RuntimeError("mất mạng")
        return good(city, model)

    client, ctx = _client(fetch)
    assert client.get("/api/risk").json()["stale"] is False
    calls["fail"] = True
    snapshot, _ = ctx.snapshots["hcm"]
    ctx.snapshots["hcm"] = (snapshot, -1e9)  # coi như bản đang giữ đã quá cũ
    body = client.get("/api/risk").json()
    assert body["stale"] is True and "mất mạng" in body["error"]
    assert body["hours"][0]["rain"]["state"] == "alert"  # vẫn là bản tính lần trước
    assert client.get("/api/health").json()["last_error"] == body["error"]


def test_rain_source_down_at_startup_still_gives_tide_and_reports(model_data):
    calls = {"fail": True}
    good = _rain(99.0)

    def fetch(city, model):
        if calls["fail"]:
            raise RuntimeError("mất mạng")
        return good(city, model)

    client, ctx = _client(fetch)
    body = client.get("/api/risk").json()
    assert body["rain_missing"] is True and body["stale"] is True and "mất mạng" in body["error"]
    assert body["states"] == {"rain": "quiet", "tide": "quiet"} and body["counts_now"] == {"high": 0, "medium": 0}
    assert body["hours"][0]["tide"]["astro_m"] == 3.2  # triều không cần mạng nên vẫn có

    calls["fail"] = False
    ctx.risk_failures.clear()  # coi như đã qua thời gian chờ thử lại
    body = client.get("/api/risk").json()
    assert body["rain_missing"] is False and body["stale"] is False and body["states"]["rain"] == "alert"


def test_city_without_model_files_is_a_404(model_data):
    client, _ = _client(_rain(0.0))
    assert client.get("/api/risk", params={"city": "danang"}).status_code == 404
    assert client.get("/api/risk", params={"city": "hanoi"}).status_code == 404
    assert client.get("/api/risk/routes", params={"city": "danang"}).status_code == 404


def test_route_layer_is_served_compressed_and_cached_by_etag(model_data):
    client, _ = _client(_rain(0.0))
    response = client.get("/api/risk/routes")
    assert response.status_code == 200 and response.headers["content-type"].startswith("application/geo+json")
    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["features"][0]["properties"]["br"] == 2
    again = client.get("/api/risk/routes", headers={"If-None-Match": response.headers["etag"]})
    assert again.status_code == 304


def test_flood_points_skip_rows_that_could_not_be_located(model_data):
    client, _ = _client(_rain(0.0))
    body = client.get("/api/risk/points").json()
    assert [f["properties"]["place"] for f in body["features"]] == ["Ngã tư thử"]
    assert body["features"][0]["geometry"]["coordinates"] == [106.7, 10.78] and body["features"][0]["properties"]["cause"] == "rain"


def test_another_machine_can_push_the_model_result_with_the_token(model_data, monkeypatch):
    from floodrisk.api import ports

    def down(city, model):
        raise RuntimeError("429")

    client, ctx = _client(down)
    record = ports.to_record(ctx.model("hcm").snapshot(fetch=_rain(99.0)))
    assert client.post("/api/risk/snapshot", json={"city": "hcm", "record": record}).status_code == 404  # chưa đặt mã: không nhận

    monkeypatch.setenv("RISK_PUSH_TOKEN", "ma-thu")
    assert client.post("/api/risk/snapshot", json={"city": "hcm", "record": record}, headers={"X-Push-Token": "sai"}).status_code == 403
    assert client.post("/api/risk/snapshot", json={"city": "hcm", "record": {}}, headers={"X-Push-Token": "ma-thu"}).status_code == 422
    assert client.post("/api/risk/snapshot", json={"city": "hcm", "record": record}, headers={"X-Push-Token": "ma-thu"}).json() == {"ok": True}
    body = client.get("/api/risk").json()
    assert body["rain_missing"] is False and body["stale"] is False and body["states"]["rain"] == "alert"
    assert body["counts_now"] == {"high": 5, "medium": 15}


def test_local_sources_are_reapplied_when_a_new_model_result_arrives(model_data, monkeypatch):
    """Lỗi ngày 08/10 trên Render: bản tính được đẩy lên báo động, nhưng số đo tại chỗ tính từ bản thiếu mưa vẫn được dùng lại."""
    from types import SimpleNamespace

    from floodrisk.api import ports

    def down(city, model):
        raise RuntimeError("429")

    client, ctx = _client(down)
    ctx.hydro_sources["hcm"] = SimpleNamespace(rain_gauges=lambda: [], gauge_hours=lambda g: [], tide_point=lambda t: (0.5, "measured"))
    monkeypatch.setenv("RISK_PUSH_TOKEN", "ma-thu")
    assert client.get("/api/risk").json()["counts_now"] == {"high": 0, "medium": 0}  # bản thiếu mưa

    record = ports.to_record(ctx.model("hcm").snapshot(fetch=_rain(99.0)))
    client.post("/api/risk/snapshot", json={"city": "hcm", "record": record}, headers={"X-Push-Token": "ma-thu"})
    body = client.get("/api/risk").json()
    assert body["states"]["rain"] == "alert" and body["counts_now"] == {"high": 5, "medium": 15} and body["overrides"] == {}
