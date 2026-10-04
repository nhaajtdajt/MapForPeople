import json

import geopandas as gpd
import pandas as pd

from floodrisk import config, contracts
from floodrisk.samples import make_sample


def test_sample_matches_contracts(monkeypatch, tmp_path):
    monkeypatch.setenv("FLOODRISK_DATA", str(tmp_path))
    make_sample(tmp_path)

    units = gpd.read_parquet(config.units_path("hcm"))
    contracts.validate_units(units)
    assert len(units) == 8 and units["unit_id"].iloc[6] == "hcm-sample06"

    scores = pd.read_parquet(config.scores_path("hcm"))
    contracts.validate(scores, contracts.SCORES, "scores")
    assert set(scores["basis"]) <= contracts.BASES and {"history", "model"} <= set(scores["basis"])
    assert scores["loc_weight"].between(0, 1).all()

    risk = pd.read_parquet(config.risk_path("hcm"))
    contracts.validate(risk, contracts.RISK_FILE, "risk")
    assert sorted(risk["hour_offset"].unique()) == [0, 1, 2]
    assert len(risk) == 3 * len(units)
    now = risk[risk["hour_offset"] == 0]
    assert (now["level"] == 2).sum() == 3 and (now["level"] == 1).sum() == 2

    cells = pd.read_parquet(config.rain_cells_path("hcm"))
    contracts.validate(cells, contracts.RAIN_CELLS, "rain_cells")

    nodes = pd.read_parquet(config.graph_nodes_path("hcm"))
    edges = gpd.read_parquet(config.graph_edges_path("hcm"))
    edge_units = pd.read_parquet(config.edge_units_path("hcm"))
    contracts.validate(nodes, contracts.GRAPH_NODES, "graph_nodes")
    contracts.validate(edges, contracts.GRAPH_EDGES, "graph_edges")
    contracts.validate(edge_units, contracts.EDGE_UNITS, "edge_units")
    assert len(nodes) == 16 and len(edges) == 48 and len(edge_units) == 48
    assert set(edge_units["unit_id"]) == set(units["unit_id"])

    trigger = json.loads(config.trigger_path("hcm").read_text(encoding="utf-8"))
    assert len(trigger["rain"]["coef"]) == 2 and trigger["rain"]["cuts"]["medium"] < trigger["rain"]["cuts"]["high"]

    choice = json.loads(config.model_choice_path().read_text(encoding="utf-8"))
    assert choice["validated"] == ["hcm"]

    index = json.loads((config.replay_dir("hcm") / "index.json").read_text(encoding="utf-8"))
    assert index[0]["id"] == "2024-10-18" and index[0]["kind"] == "recorded-day" and index[0]["recorded_count"] == 2
    replay = pd.read_parquet(config.replay_dir("hcm") / "2024-10-18.parquet")
    contracts.validate(replay, contracts.REPLAY, "replay")
    assert replay["recorded"].sum() == 2 * 3 and (replay["reporters"] == 0).all()
