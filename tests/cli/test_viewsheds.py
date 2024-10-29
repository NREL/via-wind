# -*- coding: utf-8 -*-
"""Unit tests for via_wind.cli.viewsheds module"""
import tempfile
from pathlib import Path

import pytest
import geopandas as gpd
from shapely import geometry

from via_wind.cli.viewshed import _split_turbines

# note: only includes tests for _split_turbines. all other functionality
# is tested through cli.test_cli.test_viewsheds_happy


@pytest.mark.parametrize(
    "nodes,expected_batch_size,expected_skip_features",
    [
        (1, 100, [0]),
        (2, 50, [0, 50]),
        (3, 34, [0, 34, 68]),
        (4, 25, [0, 25, 50, 75]),
        (100, 1, list(range(0, 100))),
        (200, 1, list(range(0, 100))),
    ],
)
def test_split_turbines_happy(nodes, expected_batch_size, expected_skip_features):
    """
    Happy path test for _split_turbines - check that it splits a dataset of known size
    (100 records) as expected for different numbers of nodes

    Parameters
    ----------
    nodes : _type_
        _description_
    expected_batch_size : _type_
        _description_
    expected_skip_features : _type_
        _description_
    """

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)
        df = gpd.GeoDataFrame(geometry=[geometry.Point(0, 0)] * 100, crs="EPSG:4326")
        out_gpkg = tempdir_path.joinpath("points.gpkg")
        df.to_file(out_gpkg)

        batch_size, skip_features = _split_turbines(out_gpkg, nodes)
        assert batch_size == expected_batch_size
        assert skip_features == expected_skip_features


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
