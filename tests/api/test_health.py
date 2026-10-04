from fastapi.testclient import TestClient


def test_health_reports_sample_data_and_fake_parts(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True and body["data"] == "sample" and body["test_tools"] is False
    assert set(body["parts"]) == {"evidence", "levels", "scenarios", "hourly"}
    assert set(body["parts"].values()) <= {"real", "fake"}
    assert body["traffic"]["hcm"] == {"source": "typical", "observed_at": None}
    assert body["last_refresh"] is None and body["last_error"] is None


def test_health_says_real_data_without_marker(data):
    from floodrisk.api.main import create_app

    (data / "processed" / "SAMPLE").unlink()
    assert TestClient(create_app()).get("/api/health").json()["data"] == "real"


def test_test_tools_flag_follows_environment(data, monkeypatch):
    from floodrisk.api.main import create_app

    monkeypatch.setenv("FLOODRISK_TEST_TOOLS", "1")
    assert TestClient(create_app()).get("/api/health").json()["test_tools"] is True


def test_cities_reflect_model_choice(client):
    cities = {c["key"]: c for c in client.get("/api/cities").json()}
    assert set(cities) == {"hcm", "danang"}
    assert cities["hcm"]["validated"] is True and cities["danang"]["validated"] is False
    assert cities["hcm"]["center"] == [106.70, 10.78] and cities["hcm"]["has_tide"] is True


def test_cities_without_model_choice_are_all_unvalidated(data):
    from floodrisk import config
    from floodrisk.api.main import create_app

    config.model_choice_path().unlink()
    cities = TestClient(create_app()).get("/api/cities").json()
    assert all(c["validated"] is False for c in cities)
