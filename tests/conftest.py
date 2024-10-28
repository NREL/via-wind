# -*- coding: utf-8 -*-
"""Pytest fixtures"""
from pathlib import Path
import argparse

import pytest
from click.testing import CliRunner
import numpy as np
import rasterio
import utils


from via_wind import CONFIGS_DIR

TESTS_DIR = Path(__file__).parent


@pytest.fixture
def test_cli_runner():
    """Return a click CliRunner for testing commands"""
    return CliRunner()


@pytest.fixture
def test_config():
    """Return path to simple test configuration file."""
    return CONFIGS_DIR.joinpath("test_config.json")


@pytest.fixture
def compare_images_approx():
    """Exposes the compare_images_approx function as a fixture"""
    return utils.compare_images_approx


@pytest.fixture
def check_files_match():
    """Exposes the check_files_match function as a fixture"""
    return utils.check_files_match


@pytest.fixture
def compare_csv_data():
    """Exposes the compare_csv_data function as a fixture"""
    return utils.compare_csv_data


@pytest.fixture
def test_data_dir():
    """Return path to test data directory"""
    return TESTS_DIR.joinpath("data")


@pytest.fixture
def degree_radian_pairs():
    """Returns list of tuples for known degree/radian equivalents"""
    deg_rad = [
        (0, 0),
        (90, np.pi * 0.5),
        (180, np.pi),
        (270, np.pi * 1.5),
        (360, np.pi * 2),
    ]

    return deg_rad


@pytest.fixture
def turbine_params_dict():
    """Returns dictionary containing valid turbine configuration parameters"""
    params_dict = {
        "blade_chord_m": 1.95,
        "distances_to_camera_m": [1000, 5000],
        "hub_height_m": 105.0,
        "obstruction_heights": [0, 70],
        "rotations": ["FRONT", "DIAGONAL", "SIDE"],
        "rotor_diameter_m": 90.0,
        "rotor_overhang_m": 5.2,
        "tower_diameter_m": 5.5,
    }

    return params_dict


@pytest.fixture
def camera_params_dict():
    """Returns dictionary containing valid turbine camera parameters"""
    params_dict = {
        "film_width_mm": 35,
        "height_m": 1.75,
        "lens_mm": 50,
        "output_resolution_height": 1080,
        "output_resolution_width": 1920,
    }

    return params_dict


@pytest.fixture
def raster_params():
    """
    Returns a dictionary containing parameters that can be used to mock a raster.
    """
    params = {
        "nodata": 0,
        "crs": rasterio.CRS.from_string("ESRI:102003"),
        "origin": [-672306, 413405],
        "resolution": 30,
        "shape": (135, 135),
    }
    params["affine"] = rasterio.transform.from_origin(
        *params["origin"], xsize=params["resolution"], ysize=params["resolution"]
    )

    return params


def pytest_addoption(parser):
    """
    Adds a pytest CLI option that enables running tests while skipping detailed checking
    of output content for equality to expected content.
    """
    parser.addoption(
        "--skip_content_check", action=argparse.BooleanOptionalAction, default=False
    )


def pytest_generate_tests(metafunc):
    """
    Configure pytest to read the input --skip_content_check option and pass it to
    tests that use this fixture.
    """
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".
    skip_content_check = metafunc.config.option.skip_content_check
    if "skip_content_check" in metafunc.fixturenames and skip_content_check is not None:
        metafunc.parametrize("skip_content_check", [skip_content_check])
