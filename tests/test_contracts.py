import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from floodrisk import contracts


def _risk():
    return pd.DataFrame({"unit_id": ["a", "b"], "hour_offset": [0, 0], "risk": [0.1, 0.9], "level": [0, 2],
                         "t_rain": [0.2, 0.9], "t_tide": [0.0, 0.0]})


def test_valid_table_passes():
    contracts.validate(_risk(), contracts.RISK, "risk")


def test_missing_column_names_the_column():  # Review Focus 2
    with pytest.raises(ValueError, match="level"):
        contracts.validate(_risk().drop(columns="level"), contracts.RISK, "risk")


def test_null_in_required_column_rejected():  # Review Focus 3
    df = _risk()
    df.loc[0, "unit_id"] = None
    with pytest.raises(ValueError, match="unit_id"):
        contracts.validate(df, contracts.RISK, "risk")


def test_float_in_integer_column_rejected():  # Review Focus 4
    df = _risk()
    df["level"] = df["level"].astype(float)
    with pytest.raises(ValueError, match="level"):
        contracts.validate(df, contracts.RISK, "risk")


def test_scores_and_obs_units_pass():
    scores = pd.DataFrame({
        "unit_id": ["a", "b"], "s_rain": [0.95, 0.0], "s_tide": [0.0, 0.5], "basis": ["history", "model"],
        "exact": [True, False], "loc_weight": [1.0, 0.25], "history": [3, 0],
        "max_depth_cm": [40.0, None], "last_year": [2024.0, None],
    })
    contracts.validate(scores, contracts.SCORES, "scores")
    assert set(scores["basis"]) <= contracts.BASES
    obs_units = pd.DataFrame({"obs_id": ["o1"], "unit_id": ["a"], "exact": [True], "spread_m": [180.0]})
    contracts.validate(obs_units, contracts.OBS_UNITS, "obs_units")


def _units(crs, with_terrain=True):
    value = 1.0 if with_terrain else None
    gdf = gpd.GeoDataFrame(
        {
            "unit_id": ["hcm-1"], "parent_id": ["hcm-p-1"], "city": ["hcm"], "name": ["Đường A"],
            "road_class": ["residential"], "road_rank": [1], "length_m": [100.0],
            "is_bridge": [False], "is_tunnel": [False], "rain_cell": [0],
            "elev_min": [value], "elev_mean": [value], "tpi_300": [value], "tpi_1000": [value],
            "dist_water_m": [value], "built_frac_200": [value],
        },
        geometry=[LineString([(106.7, 10.78), (106.701, 10.78)])],
        crs=crs,
    )
    features = ["elev_min", "elev_mean", "tpi_300", "tpi_1000", "dist_water_m", "built_frac_200"]
    return gdf.astype({c: "float64" for c in features})


def test_units_pass_with_and_without_terrain():  # Review Focus 5
    contracts.validate_units(_units(4326))
    contracts.validate_units(_units(4326, with_terrain=False))


def test_units_reject_wrong_crs():
    with pytest.raises(ValueError, match="4326"):
        contracts.validate_units(_units(32648))
