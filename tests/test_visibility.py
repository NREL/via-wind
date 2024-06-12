# -*- coding: utf-8 -*-
"""Unit tests for via_wind.visibility module"""
import tempfile
from pathlib import Path

import pytest
import numpy as np
import rasterio
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_string_dtype, is_integer_dtype

from via_wind import visibility, raster
from via_wind.measures import calc_distance_and_direction


def test_calc_viewshed_shape():
    """
    Unit test for calc_viewshed_shape() - test that it produces the expected
    output when passed a known input.
    """

    max_distance_km = 2
    resolution_m = 30
    expected_shape = (135, 135)

    shape = visibility.calc_viewshed_shape(max_distance_km, resolution_m)
    assert shape == expected_shape


def test_run_viewshed(raster_params):
    """
    Test for run_viewshed() - mock a flat elevation dataset and check that
    run_viewshed() produces the expected output - visible pixels everywhere within
    the maximum distance.
    """

    max_distance_km = 2
    raster_params["shape"] = visibility.calc_viewshed_shape(
        max_distance_km, raster_params["resolution"]
    )
    array = np.ones(raster_params["shape"], dtype="float32")

    with tempfile.TemporaryDirectory() as tempdir:
        output_directory = Path(tempdir)
        out_tif = output_directory.joinpath("test.tif")
        raster.save_to_geotiff(
            array,
            affine=raster_params["affine"],
            crs=raster_params["crs"],
            out_tif=out_tif,
            nodata_value=raster_params["nodata"],
        )

        center_pixel = raster_params["shape"][0] // 2
        center_point = rasterio.transform.xy(
            raster_params["affine"], center_pixel, center_pixel
        )

        result = visibility.run_viewshed(
            out_tif.as_posix(),
            turbine_x=center_point[0],
            turbine_y=center_point[1],
            turbine_z=50,
            max_distance=max_distance_km * 1000,
            viewer_z=1.75,
        )
        viewshed = result.ReadAsArray()
        assert viewshed.max() == 1
        assert viewshed.min() == 0
        # since the input elevation is flat, everything up to the maximum distance
        # should be visible
        distance, _ = calc_distance_and_direction(viewshed.shape)
        distance *= raster_params["resolution"]
        assert ((distance <= 2000) == viewshed).all()


def test_check_columns():
    """
    Unit test for check_columns() - make sure it passes for valid inputs and raises
    correct errors when columns are either missing or the wrong dtype.
    """

    df = pd.DataFrame()
    df["a"] = np.arange(0, 5).astype(float)
    df["b"] = ["b"] * 5
    df["c"] = range(0, 5)

    required_columns = {
        "a": (is_numeric_dtype, "must be numeric"),
        "b": (is_string_dtype, "must be string"),
        "c": (is_integer_dtype, "must be integer"),
    }
    visibility.check_columns(df, required_columns)

    # change a dtype and check for ValueError
    df["a"] = [str(a) for a in df["a"]]
    with pytest.raises(ValueError) as exc_info:
        visibility.check_columns(df, required_columns)
        assert exc_info.startswith("Invalid values for column")

    # drop a column and check for KeyError
    df.drop(columns=["a"], inplace=True)
    with pytest.raises(KeyError) as exc_info:
        visibility.check_columns(df, required_columns)
        assert exc_info == "Required column a not found in dataframe"


def test_get_obstruction_heights():
    """
    Unit test for get_obstruction_heights() - tests some known inputs and expected
    outputs.
    """

    rotor_diameter = 80
    hub_height = 80
    obstruction_interval = 20
    expected_results = [0, 20, 40, 60, 80, 100, 120]

    results = visibility.get_obstruction_heights(
        rotor_diameter, hub_height, obstruction_interval
    )
    assert np.array_equal(results, expected_results)

    obstruction_interval = 31
    expected_results = [0, 31, 62, 93, 124]

    results = visibility.get_obstruction_heights(
        rotor_diameter, hub_height, obstruction_interval
    )
    assert np.array_equal(results, expected_results)


def test_check_fov_lkup_complete(test_data_dir):
    """
    Unit test for check_fov_lkup_complete(). Make sure it passes and fails as expected.
    """

    turbines_df = pd.DataFrame({"rd_m": [60], "hh_m": [70]})
    obstruction_interval_m = 10
    max_distance_km = 2

    fov_df = pd.read_csv(test_data_dir.joinpath("viewsheds", "fov_lkup.csv"))

    visibility.check_fov_lkup_complete(
        fov_df, turbines_df, obstruction_interval_m, max_distance_km
    )

    with pytest.raises(
        ValueError, match="Maximum distance in FOV lookup table is smaller.*"
    ):
        visibility.check_fov_lkup_complete(
            fov_df, turbines_df, obstruction_interval_m, 3
        )

    with pytest.raises(
        ValueError, match="Required values are missing from the FOV lookup table.*"
    ):
        visibility.check_fov_lkup_complete(fov_df, turbines_df, 25, max_distance_km)


def test_bin_distances(raster_params):
    """
    Unit test for bin_distances() function. Check actual output results against
    expected results for known input.
    """
    max_distance_km = 10
    raster_params["shape"] = visibility.calc_viewshed_shape(
        max_distance_km, raster_params["resolution"]
    )
    distance_array, _ = calc_distance_and_direction(raster_params["shape"])
    distance_array *= raster_params["resolution"]

    fov_df = pd.DataFrame()
    distance_vals = [0, 500, 1000, 5000, 7500, 10000]
    fov_df["distance_m"] = distance_vals

    results = visibility.bin_distances(fov_df, distance_array)
    assert np.array_equal(np.unique(results), np.array(distance_vals))

    distance_vals.insert(0, distance_vals[0])
    distance_vals.insert(-1, distance_vals[-1])
    for i in range(1, len(distance_vals) - 1):
        value = distance_vals[i]
        lower = (distance_vals[i - 1] + value) / 2
        upper = (distance_vals[i + 1] + value) / 2
        if i == 1:
            expected_result = np.less_equal(distance_array, upper)
        elif i == (len(distance_vals) - 2):
            expected_result = np.greater(distance_array, lower)
        else:
            expected_result = np.greater(distance_array, lower) & np.less_equal(
                distance_array, upper
            )
        assert np.array_equal(expected_result, results == value)


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
