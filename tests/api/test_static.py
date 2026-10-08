"""Bản triển khai: máy chủ phục vụ luôn giao diện đã dựng, và không che các đường dẫn /api (spec 07, mục 1.1)."""
from fastapi.testclient import TestClient


def test_built_web_app_is_served_next_to_the_api(data, monkeypatch, tmp_path):
    from floodrisk.api.main import create_app

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Bản đồ nguy cơ ngập</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    monkeypatch.setenv("FLOODRISK_WEB_DIST", str(dist))
    client = TestClient(create_app())
    assert "Bản đồ nguy cơ ngập" in client.get("/").text
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/api/health").json()["ok"] is True
    assert client.get("/api/khong-co").status_code == 404


def test_without_a_built_web_app_only_the_api_answers(data, monkeypatch, tmp_path):
    from floodrisk.api.main import create_app

    monkeypatch.setenv("FLOODRISK_WEB_DIST", str(tmp_path / "chua-dung"))
    client = TestClient(create_app())
    assert client.get("/").status_code == 404 and client.get("/api/health").status_code == 200
