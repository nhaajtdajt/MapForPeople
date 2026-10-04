import httpx
import pytest

from floodrisk.api.goong import Goong, GoongError


def _goong(handler, key="KEY"):
    return Goong(key, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_autocomplete_maps_fields_and_sends_key():
    seen = {}

    def handler(request):
        seen.update(dict(request.url.params), path=request.url.path)
        return httpx.Response(200, json={"predictions": [
            {"place_id": "p1", "description": "A, B", "structured_formatting": {"main_text": "A", "secondary_text": "B"}},
            {"place_id": "p2", "description": "Chỉ có mô tả"},
        ]})

    out = _goong(handler).autocomplete("nguyen hue", lat=10.78, lon=106.70)
    assert out == [{"place_id": "p1", "main": "A", "secondary": "B"},
                   {"place_id": "p2", "main": "Chỉ có mô tả", "secondary": ""}]
    assert seen["path"] == "/v2/place/autocomplete" and seen["api_key"] == "KEY" and seen["location"] == "10.78,106.7"


def test_place_detail():
    def handler(request):
        return httpx.Response(200, json={"result": {"name": "Chợ", "formatted_address": "1 Lê Lợi",
                                                    "geometry": {"location": {"lat": 10.77, "lng": 106.69}}}})

    assert _goong(handler).place("p1") == {"name": "Chợ", "address": "1 Lê Lợi", "lat": 10.77, "lon": 106.69}


def test_place_without_coordinates_is_an_error():
    with pytest.raises(GoongError, match="tọa độ"):
        _goong(lambda request: httpx.Response(200, json={"result": {"name": "x"}})).place("p1")


def test_reverse_returns_first_result():
    seen = {}

    def handler(request):
        seen.update(dict(request.url.params), path=request.url.path)
        return httpx.Response(200, json={"results": [
            {"name": "Công trường Quách Thị Trang", "formatted_address": "Công trường Quách Thị Trang, Bến Thành",
             "place_id": "abc"},
            {"name": "khác", "formatted_address": "khác", "place_id": "zzz"},
        ]})

    out = _goong(handler).reverse(10.7725, 106.698)
    assert out == {"name": "Công trường Quách Thị Trang", "address": "Công trường Quách Thị Trang, Bến Thành", "place_id": "abc"}
    assert seen["path"] == "/v2/geocode" and seen["latlng"] == "10.7725,106.698"


def test_reverse_with_no_result_is_empty_not_an_error():
    out = _goong(lambda request: httpx.Response(200, json={"results": []})).reverse(1, 2)
    assert out == {"name": "", "address": "", "place_id": None}


def test_http_error_and_network_error_become_goong_error():
    with pytest.raises(GoongError, match="403"):
        _goong(lambda request: httpx.Response(403, json={"error": "bad key"})).autocomplete("x")

    def broken(request):
        raise httpx.ConnectError("mất mạng")

    with pytest.raises(GoongError):
        _goong(broken).place("p1")


def test_missing_key_is_reported_without_a_request():
    def never(request):
        raise AssertionError("không được gọi mạng khi thiếu khóa")

    with pytest.raises(GoongError, match="GOONG_API_KEY"):
        _goong(never, key="").autocomplete("x")


def test_places_endpoints(client):
    class Fake:
        def autocomplete(self, q, lat=None, lon=None, limit=6):
            return [{"place_id": "p1", "main": q, "secondary": f"{lat},{lon}"}]

        def place(self, place_id):
            raise GoongError("HTTP 403")

        def reverse(self, lat, lon):
            return {"name": "Điểm", "address": f"{lat},{lon}", "place_id": None}

    client.app.state.ctx.goong = Fake()
    res = client.get("/api/places/autocomplete", params={"q": "cho", "lat": 10.78, "lon": 106.7})
    assert res.json() == [{"place_id": "p1", "main": "cho", "secondary": "10.78,106.7"}]
    assert client.get("/api/places/autocomplete", params={"q": " "}).json() == []

    bad = client.get("/api/places/detail", params={"place_id": "p1"})
    assert bad.status_code == 502 and "Không tìm được địa điểm" in bad.json()["detail"]

    ok = client.get("/api/places/reverse", params={"lat": 10.77, "lon": 106.69})
    assert ok.status_code == 200 and ok.json()["name"] == "Điểm"


def test_reverse_rejects_points_outside_vietnam_before_calling_goong(client):
    class Boom:
        def reverse(self, lat, lon):
            raise AssertionError("không được gọi Goong")

    client.app.state.ctx.goong = Boom()
    res = client.get("/api/places/reverse", params={"lat": 48.85, "lon": 2.35})
    assert res.status_code == 422 and "Việt Nam" in res.json()["detail"]


def test_goong_failure_on_reverse_is_502_with_vietnamese_detail(client):
    class Down:
        def reverse(self, lat, lon):
            raise GoongError("không kết nối được")

    client.app.state.ctx.goong = Down()
    res = client.get("/api/places/reverse", params={"lat": 10.77, "lon": 106.69})
    assert res.status_code == 502 and "Không tìm được địa điểm" in res.json()["detail"]
