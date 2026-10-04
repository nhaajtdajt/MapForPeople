import json

import geopandas as gpd
import pandas as pd

from floodrisk import config, contracts
from floodrisk.api import devdata


def test_dev_data_covers_both_cities_and_matches_contracts(data):
    for city in config.CITIES:
        units = gpd.read_parquet(config.units_path(city))
        contracts.validate_units(units)
        scores = pd.read_parquet(config.scores_path(city))
        observations = pd.read_parquet(config.observations_path(city))
        obs_units = pd.read_parquet(config.obs_units_path(city))
        contracts.validate(observations, contracts.OBSERVATIONS, "observations")
        contracts.validate(obs_units, contracts.OBS_UNITS, "obs_units")
        # mỗi đoạn có đúng `history` ghi nhận
        counts = observations.groupby("unit_id").size()
        for row in scores.itertuples():
            assert counts.get(row.unit_id, 0) == row.history
        assert set(obs_units["obs_id"]) == set(observations["obs_id"])


def test_marker_and_model_choice(data):
    assert (data / "processed" / "SAMPLE").exists()
    assert json.loads(config.model_choice_path().read_text(encoding="utf-8"))["validated"] == ["hcm"]


def test_risk_is_fresh_unless_stale_requested(data, tmp_path_factory):
    fresh = pd.read_parquet(config.risk_path("hcm"))["computed_at"].iloc[0]
    assert (devdata.vietnam_now() - fresh) < pd.Timedelta(hours=2)

    other = tmp_path_factory.mktemp("stale")
    devdata.make_dev_data(other, stale=True)
    old = pd.read_parquet(other / "processed" / "hcm" / "risk.parquet")["computed_at"].iloc[0]
    assert old == pd.Timestamp("2026-10-04 08:00:00")


def test_rising_scenario_has_high_level_only_at_hour_two_and_four_reporters(data):
    index = json.loads((config.replay_dir("hcm") / "index.json").read_text(encoding="utf-8"))
    ids = {row["id"]: row for row in index}
    assert {"2024-10-18", devdata.SYNTHETIC_ID} <= set(ids) and ids[devdata.SYNTHETIC_ID]["kind"] == "synthetic"

    frame = pd.read_parquet(config.replay_dir("hcm") / f"{devdata.SYNTHETIC_ID}.parquet")
    contracts.validate(frame, contracts.REPLAY, "replay")
    unit6 = frame[frame["unit_id"] == "hcm-sample06"].set_index("hour_offset")["level"]
    assert list(unit6) == [0, 1, 2]  # khô ở giờ 0, cao ở giờ 2: lời khuyên "nên đi ngay" của spec 06

    reported = frame[(frame["unit_id"] == "hcm-sample02") & (frame["hour_offset"] == 0)].iloc[0]
    assert reported["reporters"] == 4 and reported["reported_level"] == 3 and reported["level"] == 2
    assert (frame[frame["hour_offset"] > 0]["reporters"] == 0).all()
