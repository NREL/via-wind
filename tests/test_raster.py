# -*- coding: utf-8 -*-
"""Unit tests for via_wind.raster module"""
import tempfile
from pathlib import Path
import shutil

import pytest
import rasterio
import numpy as np
from shapely.geometry import box

from via_wind import raster


def test_save_to_geotiff(raster_params):
    """
    Unit test for save_to_geotiff() - test writing an array to a file and then open the
    raster and compare to expcted attributes and data.
    """
    array = np.ones(raster_params["shape"], dtype="float32")
    array[0, :] = raster_params["nodata"]

    with tempfile.TemporaryDirectory() as tempdir:
        output_directory = Path(tempdir)
        tags = {"TEST": "VALUE"}
        out_tif = output_directory.joinpath("test.tif")
        raster.save_to_geotiff(
            array,
            affine=raster_params["affine"],
            crs=raster_params["crs"],
            out_tif=out_tif,
            nodata_value=raster_params["nodata"],
            tags=tags,
        )

        # open the raster and check everything is as expected
        with rasterio.open(out_tif, "r") as rast:
            assert rast.crs == raster_params["crs"]
            assert rast.res == (
                raster_params["resolution"],
                raster_params["resolution"],
            )
            assert rast.transform == raster_params["affine"]
            assert rast.shape == array.shape
            assert rast.nodata == raster_params["nodata"]
            assert (
                np.array([rast.bounds.left, rast.bounds.top])
                == np.array(raster_params["origin"])
            ).all()
            assert (rast.read() == array).all()
            assert rast.tags().get("TEST") == tags.get("TEST")


def test_save_to_geotiff_bad_dtype(raster_params):
    """
    Unit test  for save_to_geotiff to ensure it raises a TypeError when the input array
    has an invalid data type.
    """
    array = np.ones(raster_params["shape"], dtype="bool")

    with tempfile.TemporaryDirectory() as tempdir:
        output_directory = Path(tempdir)
        out_tif = output_directory.joinpath("test.tif")
        with pytest.raises(TypeError) as exc_info:
            raster.save_to_geotiff(
                array,
                affine=raster_params["affine"],
                crs=raster_params["crs"],
                out_tif=out_tif,
                nodata_value=raster_params["nodata"],
            )
            assert exc_info.startswith("Invalid array dtype:")


def test_get_raster_info(raster_params):
    """
    Unit test for get_raster_info - write an output raster using save_to_geotiff() then
    check that get_raster_info() returns the correct crs and resolution.
    """
    array = np.ones(raster_params["shape"], dtype="int8")
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

        raster_info = raster.get_raster_info(out_tif)
        assert raster_info["crs"] == raster_params["crs"]
        assert raster_info["resolution"] == raster_params["resolution"]


def test_get_raster_info_bad_resolution(raster_params):
    """
    Test that get_raster_info() raises a ValueError when reading a raster that has
    different horizontal and vertical resolutions.
    """
    array = np.ones(raster_params["shape"], dtype="int8")
    affine = raster_params["affine"]
    new_affine = rasterio.Affine(35, affine.b, affine.c, affine.d, affine.e, affine.f)

    with tempfile.TemporaryDirectory() as tempdir:
        output_directory = Path(tempdir)
        out_tif = output_directory.joinpath("test.tif")
        raster.save_to_geotiff(
            array,
            affine=new_affine,
            crs=raster_params["crs"],
            out_tif=out_tif,
            nodata_value=raster_params["nodata"],
        )

        with pytest.raises(ValueError) as exc_info:
            raster.get_raster_info(out_tif)
            assert exc_info.startswith(
                "Input raster resolution is not the same in the X and Y dimensions"
            )


def test_validate_crs_units():
    """
    Unit test for validate_crs_units() - check that a CRS in meters passes, while a CRS
    in decimal degrees raises a ValueError.
    """

    good_crs = rasterio.CRS.from_string("ESRI:102003")
    bad_crs = rasterio.CRS.from_string("EPSG:4326")

    raster.validate_crs_units(good_crs)
    with pytest.raises(ValueError) as exc_info:
        raster.validate_crs_units(bad_crs)
        assert exc_info.startswith(
            "Input raster CRS must have one of the following linear units"
        )


def test_create_vrt(test_data_dir, skip_content_check):
    """
    Unit test for create_vrt: test that it creates a VRT with the expected contents
    when passed known inputs.
    """

    with tempfile.TemporaryDirectory() as tempdir:
        output_directory = Path(tempdir)

        # copy the source tifs so the paths in the VRT are relative
        # (this makes it easier to test the VRT contents)
        src_tifs_path = test_data_dir.joinpath("vrt", "inputs")
        copy_tifs_path = output_directory.joinpath("tifs")
        shutil.copytree(src_tifs_path, copy_tifs_path)

        out_vrt = output_directory.joinpath("test.vrt")
        raster.create_vrt(copy_tifs_path, out_vrt_path=out_vrt)

        assert out_vrt.exists()
        if not skip_content_check:
            expected_vrt = test_data_dir.joinpath("vrt", "test.vrt")
            with open(expected_vrt, "r", encoding="utf-8") as f:
                expected_contents = f.read()
            with open(out_vrt, "r", encoding="utf-8") as f:
                output_contents = f.read()
            assert expected_contents == output_contents


def test_read_vrt_sources(test_data_dir):
    """
    Unit test for read_vrt_sources: test that it is able to read and correctly parse
    the contents of a known VRT file.
    """
    vrt_path = test_data_dir.joinpath("vrt", "test.vrt")
    vrt_df = raster.read_vrt_sources(vrt_path=vrt_path)
    assert len(vrt_df) == 2
    assert vrt_df["src_file"].tolist() == [
        "tifs/fov-pct_gid1.tif",
        "tifs/fov-pct_gid2.tif",
    ]
    assert vrt_df["bounds"].tolist() == [[0, 0, 135, 135]] * 2
    assert vrt_df.geometry.tolist() == [box(0, 0, 135, 135)] * 2


def test_merge_tifs(test_data_dir):
    """
    Unit test for merge_tifs: test that it produces the correct output when provided
    known inputs.
    """
    tif_path = test_data_dir.joinpath(
        "viewsheds", "expected_results", "fov-pct_gid1.tif"
    )
    with tempfile.TemporaryDirectory() as tempdir:
        output_directory = Path(tempdir)

        # copy the raster over to the temp directory
        shutil.copyfile(tif_path, output_directory.joinpath("1.tif"))
        # create another copy of the raster, shifted one raster extent to the right
        with rasterio.open(tif_path, "r") as rast:
            transform = rast.transform
            shifted_origin = (rast.width, 0) * transform
            shifted_transform = rasterio.transform.from_origin(
                *shifted_origin, rast.res[0], rast.res[0]
            )
            raster.save_to_geotiff(
                rast.read(1),
                affine=shifted_transform,
                crs=rast.crs,
                out_tif=output_directory.joinpath("2.tif"),
            )

        merged_tif_path = output_directory.joinpath("merge.tif")
        raster.merge_tifs(tifs_path=output_directory, out_tif_path=merged_tif_path)

        assert merged_tif_path.exists()

        # merged output should be equal to the input tif stacked twice side by side
        with rasterio.open(merged_tif_path, "r") as rast:
            merged_array = rast.read(1)
        with rasterio.open(tif_path, "r") as rast:
            input_array = rast.read(1)
        expected_array = np.concatenate((input_array, input_array), axis=1)
        assert np.array_equal(merged_array, expected_array)


def test_mosaic_block(test_data_dir):
    """
    Unit test for mosaic block: test that it produces expected output for known inputs.
    """

    vrt_path = test_data_dir.joinpath("vrt", "test.vrt")
    vrt_df = raster.read_vrt_sources(vrt_path=vrt_path)
    vrt_df["src_file"] = list(test_data_dir.joinpath("vrt", "inputs").glob("*.tif"))

    vrt_info = raster.get_raster_info(vrt_path)
    col = 10
    row = 5
    block_size = 50

    with tempfile.TemporaryDirectory() as tempdir:
        output_directory = Path(tempdir)

        raster.mosaic_block(
            vrt_df,
            vrt_info["profile"],
            output_directory,
            col_offset=col,
            row_offset=row,
            block_size=block_size,
        )
        output_block = output_directory.joinpath(f"block_{row}_{col}.tif")
        assert output_block.exists()

        with rasterio.open(output_block, "r") as rast:
            result_array = rast.read(1)

        src_tif = vrt_df["src_file"].tolist()[0]
        with rasterio.open(src_tif, "r") as rast:
            input_array = rast.read(1)
        expected_array = input_array[row : row + block_size, col : col + block_size] * 2

        assert np.array_equal(result_array, expected_array)


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
