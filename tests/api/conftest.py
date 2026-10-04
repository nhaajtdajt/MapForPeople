import pytest
from fastapi.testclient import TestClient

from floodrisk.api.devdata import make_dev_data


@pytest.fixture
def data(monkeypatch, tmp_path):
    monkeypatch.setenv("FLOODRISK_DATA", str(tmp_path))
    monkeypatch.setenv("REFRESH_MINUTES", "0")
    monkeypatch.delenv("FLOODRISK_TEST_TOOLS", raising=False)
    make_dev_data(tmp_path)
    return tmp_path


@pytest.fixture
def client(data):
    from floodrisk.api.main import create_app

    return TestClient(create_app())
