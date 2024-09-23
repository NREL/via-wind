# -*- coding: utf-8 -*-
"""Tests for via_wind.gaps_cli"""
import tempfile
from pathlib import Path
import json

import pytest
import rasterio
import numpy as np
import geopandas as gpd
from shapely import geometry

from via_wind.cli.cli import main
from via_wind import visibility, raster


def test_main(test_cli_runner):
    """Test main() CLI command."""
    result = test_cli_runner.invoke(main)
    assert result.exit_code == 0


def test_silouettes_happy(
    test_cli_runner,
    test_config,
    test_data_dir,
    check_files_match,
    compare_images_approx,
    skip_content_check,
):
    """
    Happy path integration tests for the silouettes command. Checks that all expected
    output images are created and that the output images match the expected images.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)

        # set up config data
        config_data = {
            "silouette_configs": test_config.as_posix(),
        }
        # write to json
        config_path = tempdir_path.joinpath("config.json")
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # run the command
        result = test_cli_runner.invoke(
            main,
            ["silouettes", "-c", config_path.as_posix()],
        )
        assert result.exit_code == 0

        # check all the expected outputs were created
        output_path = tempdir_path.joinpath("silouettes")
        outputs_match, difference = check_files_match(
            "[!.]*", output_path, test_data_dir.joinpath("silouette_outputs")
        )
        if not outputs_match:
            raise AssertionError(
                f"Output files do not match expected files. Difference is: {difference}"
            )

        # check outputs were created correctly
        if not skip_content_check:
            output_image_names = [
                f.relative_to(output_path) for f in output_path.rglob("*.png")
            ]
            for output_image_name in output_image_names:
                output_image = output_path.joinpath(output_image_name)
                test_image = test_data_dir.joinpath(
                    "silouette_outputs", output_image_name
                )
                images_match, pct_diff = compare_images_approx(
                    output_image, test_image, hash_size=12, max_diff_pct=0.25
                )
                assert images_match, (
                    f"{output_image_name} does match expected image. "
                    f"Percent difference is: {round(pct_diff * 100, 2)}."
                )


def test_fov_happy(test_cli_runner, test_data_dir, check_files_match, compare_csv_data):
    """
    Happy path integration tests for the fov command. Checks that the expected CSV is
    created with the expected contents.
    """

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)

        # set up config data
        silouette_directory = test_data_dir.joinpath("silouette_outputs", "test")
        config_data = {"silouette_directories": silouette_directory.as_posix()}
        # write to json
        config_path = tempdir_path.joinpath("config.json")
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        result = test_cli_runner.invoke(
            main,
            ["fov", "-c", config_path.as_posix()],
        )
        assert result.exit_code == 0

        # check all the expected outputs were created
        output_path = tempdir_path.joinpath("fov")
        outputs_match, difference = check_files_match(
            "[!.]*", output_path, test_data_dir.joinpath("fov_output")
        )
        if not outputs_match:
            raise AssertionError(
                f"Output files do not match expected files. Difference is: {difference}"
            )

        # check output was created correctly
        output_csv_names = [
            f.relative_to(output_path) for f in output_path.rglob("*.csv")
        ]
        for output_csv_name in output_csv_names:
            output_csv = output_path.joinpath(output_csv_name)
            test_csv = test_data_dir.joinpath("fov_output", output_csv_name)
            compare_csv_data(output_csv, test_csv)


def test_viewsheds_happy(
    test_cli_runner, test_data_dir, raster_params, check_files_match
):
    """
    Integration test for the viewsheds command. Tests that it produces the expected
    output for known inputs.
    """

    max_distance_km = 2

    # create the elevation raster (constant height of 1)
    raster_params["shape"] = visibility.calc_viewshed_shape(
        max_distance_km, raster_params["resolution"]
    )
    array = np.ones(raster_params["shape"], dtype="float32")

    # create the turbines geodataframe
    center_pixel = raster_params["shape"][0] // 2
    center_point = rasterio.transform.xy(
        raster_params["affine"], center_pixel, center_pixel
    )

    turbine_attributes = [
        # all of these are the same - equal to evaluating a single direction pointing N
        {
            "gid": 1,
            "rd_m": 60.0,
            "hh_m": 70.0,
            "freq_winddir_0": 1.0,
            "freq_winddir_45": 0.0,
            "freq_winddir_90": 0.0,
            "freq_winddir_135": 0.0,
            "freq_winddir_180": 0.0,
            "freq_winddir_225": 0.0,
            "freq_winddir_270": 0.0,
            "freq_winddir_315": 0.0,
        },
        {
            "gid": 2,
            "rd_m": 60.0,
            "hh_m": 70.0,
            "freq_winddir_0": 0.0,
            "freq_winddir_45": 0.0,
            "freq_winddir_90": 0.0,
            "freq_winddir_135": 0.0,
            "freq_winddir_180": 1.0,
            "freq_winddir_225": 0.0,
            "freq_winddir_270": 0.0,
            "freq_winddir_315": 0.0,
        },
        {
            "gid": 3,
            "rd_m": 60.0,
            "hh_m": 70.0,
            "freq_winddir_0": 0.5,
            "freq_winddir_45": 0.0,
            "freq_winddir_90": 0.0,
            "freq_winddir_135": 0.0,
            "freq_winddir_180": 0.5,
            "freq_winddir_225": 0.0,
            "freq_winddir_270": 0.0,
            "freq_winddir_315": 0.0,
        },
        {
            "gid": 4,
            "rd_m": 60.0,
            "hh_m": 70.0,
            "freq_winddir_0": 2,
            "freq_winddir_45": 0.0,
            "freq_winddir_90": 0.0,
            "freq_winddir_135": 0.0,
            "freq_winddir_180": 2,
            "freq_winddir_225": 0.0,
            "freq_winddir_270": 0.0,
            "freq_winddir_315": 0.0,
        },
        # these two are the same equally weighted in all directions
        {
            "gid": 5,
            "rd_m": 60.0,
            "hh_m": 70.0,
            "freq_winddir_0": 0.125,
            "freq_winddir_45": 0.125,
            "freq_winddir_90": 0.125,
            "freq_winddir_135": 0.125,
            "freq_winddir_180": 0.125,
            "freq_winddir_225": 0.125,
            "freq_winddir_270": 0.125,
            "freq_winddir_315": 0.125,
        },
        {
            "gid": 6,
            "rd_m": 60.0,
            "hh_m": 70.0,
            "freq_winddir_0": 0.125,
            "freq_winddir_45": 0.125,
            "freq_winddir_90": 0.125,
            "freq_winddir_135": 0.125,
            "freq_winddir_180": 0.0,
            "freq_winddir_225": 0.0,
            "freq_winddir_270": 0.0,
            "freq_winddir_315": 0.0,
        },
    ]
    turbines_df = gpd.GeoDataFrame(
        turbine_attributes,
        geometry=[geometry.Point(*center_point)] * len(turbine_attributes),
        crs=raster_params["crs"].to_wkt(),
    )

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)

        # save out the elevation array to geotiff
        elevation_tif = tempdir_path.joinpath("elevation.tif")
        raster.save_to_geotiff(
            array,
            affine=raster_params["affine"],
            crs=raster_params["crs"],
            out_tif=elevation_tif,
            nodata_value=None,
        )
        # save out the turbines to geopackage
        turbines_path = tempdir_path.joinpath("turbines.gpkg")
        turbines_df.to_file(turbines_path)

        fov_lkup_fpath = test_data_dir.joinpath("viewsheds", "fov_lkup.csv")

        # set up config data
        config_data = {
            "execution_control": {"nodes": 2},
            "elev_fpath": elevation_tif.as_posix(),
            "turbines_fpath": turbines_path.as_posix(),
            "fov_lkup_fpath": fov_lkup_fpath.as_posix(),
            "max_dist_km": max_distance_km,
            "obstruction_interval_m": 10,
            "viewer_height_m": 1.75,
        }
        # write to json
        config_path = tempdir_path.joinpath("config.json")
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # run the command
        result = test_cli_runner.invoke(
            main,
            ["viewsheds", "-c", config_path.as_posix()],
        )
        assert result.exit_code == 0

        output_path = tempdir_path.joinpath("viewsheds")
        # check that the same outputs are created
        expected_results_path = test_data_dir.joinpath("viewsheds", "expected_results")
        outputs_match, difference = check_files_match(
            "*.tif", output_path, expected_results_path
        )
        if not outputs_match:
            raise AssertionError(
                f"Output files do not match expected files. Difference is: {difference}"
            )

        # check the resulting tif is the same
        result_tifs = output_path.rglob("fov-pct*.tif")
        for result_tif in result_tifs:
            expected_tif = expected_results_path.joinpath(result_tif.name)
            with (
                rasterio.open(result_tif, "r") as rast1,
                rasterio.open(expected_tif, "r") as rast2,
            ):
                assert np.allclose(rast1.read(), rast2.read())


def test_merge_happy(test_cli_runner, test_data_dir):
    """
    Integration test for the merge command. Tests that it produces the expected
    output for known inputs.
    """

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)

        # copy test FOV output to two identical new rasters for merging
        inputs_path = test_data_dir.joinpath("vrt", "inputs")

        # set up config data
        inputs_path = test_data_dir.joinpath("vrt", "inputs")
        config_data = {"viewsheds_directory": inputs_path.as_posix(), "block_size": 50}
        # write to json
        config_path = tempdir_path.joinpath("config.json")
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        result = test_cli_runner.invoke(
            main,
            ["merge", "-c", config_path.as_posix()],
        )
        assert result.exit_code == 0

        output_path = tempdir_path.joinpath("viewsheds_merge")
        output_files = [
            f.relative_to(output_path) for f in output_path.rglob("[!.]*.*")
        ]
        expected_outputs = [
            Path("fov-pct_sum.tif"),
            Path("sources.vrt"),
            Path("blocks/block_0_0.tif"),
            Path("blocks/block_0_50.tif"),
            Path("blocks/block_0_100.tif"),
            Path("blocks/block_50_0.tif"),
            Path("blocks/block_50_50.tif"),
            Path("blocks/block_50_100.tif"),
            Path("blocks/block_100_0.tif"),
            Path("blocks/block_100_50.tif"),
            Path("blocks/block_100_100.tif"),
        ]
        difference = list(set(output_files).symmetric_difference(set(expected_outputs)))
        if len(difference) != 0:
            raise AssertionError(
                f"Output files do not match expected files. Difference is: {difference}"
            )

        # the input rasters are identical, so the output raster should be equal to
        # 2 * either of the the inputs
        out_sum_tif = output_path.joinpath("fov-pct_sum.tif")
        viewsheds_tif = inputs_path.joinpath("fov-pct_gid1.tif")
        with rasterio.open(viewsheds_tif, "r") as rast:
            expected_array = rast.read()

        expected_array *= 2
        with rasterio.open(out_sum_tif, "r") as rast:
            result_array = rast.read()

        assert np.array_equal(expected_array, result_array)


def test_calibrate_happy(test_cli_runner, test_data_dir):
    """
    Integration test for the calibrate command. Tests that it produces the expected
    output for known inputs.
    """

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)

        # set up config for merge step
        inputs_path = test_data_dir.joinpath("vrt", "inputs")
        merge_config_data = {
            "viewsheds_directory": inputs_path.as_posix(),
            "block_size": 50,
        }
        # write to json
        merge_config_path = tempdir_path.joinpath("config_merge.json")
        with open(merge_config_path, "w") as f:
            json.dump(merge_config_data, f)
        # run merge
        result = test_cli_runner.invoke(
            main,
            ["merge", "-c", merge_config_path.as_posix()],
        )
        assert result.exit_code == 0

        # set up config for calibrate step
        inputs_path = test_data_dir.joinpath("vrt", "inputs")
        calibrate_config_data = {
            "merge_directory": tempdir_path.joinpath("viewsheds_merge").as_posix()
        }
        # write to json
        calibrate_config_path = tempdir_path.joinpath("config_calibrate.json")
        with open(calibrate_config_path, "w") as f:
            json.dump(calibrate_config_data, f)
        # run calibrate
        result = test_cli_runner.invoke(
            main,
            ["calibrate", "-c", calibrate_config_path.as_posix()],
        )
        assert result.exit_code == 0

        output_path = tempdir_path.joinpath("viewsheds_calibrated")
        output_files = [
            f.relative_to(output_path) for f in output_path.rglob("[!.]*.*")
        ]
        expected_outputs = [
            Path("visual_impact.tif"),
            Path("blocks/block_0_0.tif"),
            Path("blocks/block_0_50.tif"),
            Path("blocks/block_0_100.tif"),
            Path("blocks/block_50_0.tif"),
            Path("blocks/block_50_50.tif"),
            Path("blocks/block_50_100.tif"),
            Path("blocks/block_100_0.tif"),
            Path("blocks/block_100_50.tif"),
            Path("blocks/block_100_100.tif"),
        ]
        difference = list(set(output_files).symmetric_difference(set(expected_outputs)))
        if len(difference) != 0:
            raise AssertionError(
                f"Output files do not match expected files. Difference is: {difference}"
            )

        expected_ratings_tif = test_data_dir.joinpath(
            "calibrate", "expected_results", "visual_impact.tif"
        )
        with rasterio.open(expected_ratings_tif, "r") as rast:
            expected_array = rast.read()

        output_ratings_tif = output_path.joinpath("visual_impact.tif")
        with rasterio.open(output_ratings_tif, "r") as rast:
            result_array = rast.read()

        assert np.array_equal(expected_array, result_array)


def test_mask_happy(test_cli_runner, test_data_dir):
    """
    Integration test for the mask command. Tests that it produces the expected
    output for known inputs.
    """

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)

        # set up config for merge step
        in_raster = test_data_dir.joinpath(
            "calibrate", "expected_results/visual_impact.tif"
        )
        mask_raster = test_data_dir.joinpath(
            "mask", "no_vis_mask.tif"
        )

        config_data = {
            "input_raster": in_raster.as_posix(),
            "mask_raster": mask_raster.as_posix(),
        }
        # write to json
        config_path = tempdir_path.joinpath("config.json")
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        result = test_cli_runner.invoke(
            main,
            ["mask", "-c", config_path.as_posix()],
        )
        assert result.exit_code == 0

        output_path = tempdir_path.joinpath("mask")
        masked_tif = output_path.joinpath(in_raster.name)
        assert masked_tif.exists(), f"Expected output raster {masked_tif} not created"

        expected_mask_tif = test_data_dir.joinpath(
            "mask", "expected_results", "visual_impact.tif"
        )
        with rasterio.open(expected_mask_tif, "r") as rast:
            expected_array = rast.read()

        with rasterio.open(masked_tif, "r") as rast:
            result_array = rast.read()

        assert np.array_equal(expected_array, result_array)

if __name__ == "__main__":
    pytest.main([__file__, "-s", "--skip_content_check"])
