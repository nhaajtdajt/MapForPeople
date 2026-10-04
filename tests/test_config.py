import pytest

from floodrisk import config


def test_cities_have_valid_bbox_and_center():
    assert set(config.CITIES) == {"hcm", "danang"}
    for city in config.CITIES.values():
        west, south, east, north = city.bbox
        assert west < east and south < north
        lon, lat = city.center
        assert west < lon < east and south < lat < north


def test_grid_cells_nest_and_levels_are_ordered():
    assert config.PARENT_CELL_M % config.GRID_CELL_M == 0
    assert 0 < config.LEVEL_MEDIUM < config.LEVEL_HIGH < 1


def test_data_dir_follows_env(monkeypatch, tmp_path):
    monkeypatch.setenv("FLOODRISK_DATA", str(tmp_path))
    assert config.data_dir() == tmp_path
    assert config.units_path("hcm") == tmp_path / "processed" / "hcm" / "units.parquet"
    assert config.obs_units_path("hcm") == tmp_path / "processed" / "hcm" / "obs_units.parquet"
    assert config.trigger_path("hcm") == tmp_path / "processed" / "hcm" / "model" / "trigger.json"
    assert config.replay_dir("hcm") == tmp_path / "processed" / "hcm" / "replay"
    assert config.graph_nodes_path("hcm") == tmp_path / "processed" / "hcm" / "graph_nodes.parquet"
    assert config.graph_edges_path("hcm") == tmp_path / "processed" / "hcm" / "graph_edges.parquet"
    assert config.edge_units_path("hcm") == tmp_path / "processed" / "hcm" / "edge_units.parquet"
    assert config.inputs_dir("hcm") == tmp_path / "raw" / "inputs" / "hcm"
    assert config.model_choice_path() == tmp_path / "processed" / "model_choice.json"
    assert config.live_dir() == tmp_path / "raw" / "live"


def test_unknown_city_raises():  # Review Focus 1
    with pytest.raises(KeyError, match="hanoi"):
        config.processed_dir("hanoi")
