# -*- coding: utf-8 -*-
"""Unit tests for via_wind.config module"""
import pytest

from via_wind.config import SilouettesConfig, TurbineParams, CameraParams


def test_turbineparams_happy(turbine_params_dict):
    """
    Happy path unit test for TurbineParams class: load a valid dictionary of
    turbine parameters.
    """
    TurbineParams(turbine_params_dict)


def test_turbineparams_missing_value(turbine_params_dict):
    """
    Test that TurbineParams class raises a ValueError when a required parameter
    is missing.
    """
    turbine_params_dict.pop("tower_diameter_m")
    with pytest.raises(ValueError) as excinfo:
        TurbineParams(turbine_params_dict)
        assert excinfo.value.message == "tower_diameter_m is missing from input."


def test_turbineparams_bad_dtype(turbine_params_dict):
    """
    Test that TurbineParams class raises a TypeError when a required parameter
    is the wrong dtype.
    """
    turbine_params_dict["rotor_overhang_m"] = "not-a-number"
    with pytest.raises(TypeError) as excinfo:
        TurbineParams(turbine_params_dict)
        assert excinfo.value.message == (
            "Invalid input for rotor_overhang_m: must be type "
            "<class 'numbers.Number'>"
        )


def test_turbineparams_bad_subelement_dtype(turbine_params_dict):
    """
    Test that TurbineParams class raises a TypeError when a required parameter
    has subelements of the wrong dtype.
    """
    turbine_params_dict["rotations"] = [1, 2, 3]
    with pytest.raises(TypeError) as excinfo:
        TurbineParams(turbine_params_dict)
        assert excinfo.value.message == (
            "Invalid input for rotations: elements must be type "
            "<class 'numbers.Number'>"
        )


def test_cameraparams_happy(camera_params_dict):
    """
    Happy path unit test for CameraParams class: load a valid dictionary of
    camera parameters.
    """
    CameraParams(camera_params_dict)


def test_cameraparams_missing_value(camera_params_dict):
    """
    Test that CameraParams class raises a ValueError when a required parameter
    is missing.
    """
    camera_params_dict.pop("lens_mm")
    with pytest.raises(ValueError) as excinfo:
        CameraParams(camera_params_dict)
        assert excinfo.value.message == "lens_mm is missing from input."


def test_cameraparams_bad_dtype(camera_params_dict):
    """
    Test that CameraParams class raises a TypeError when a required parameter
    is the wrong dtype.
    """
    camera_params_dict["lens_mm"] = "not-a-number"
    with pytest.raises(TypeError) as excinfo:
        CameraParams(camera_params_dict)
        assert excinfo.value.message == (
            "Invalid input for lens_mm: must be type <class 'numbers.Number'>"
        )


def test_config_happy(test_config):
    """
    Happy path unit test for Config() class. Confirm that it can load configuration from
    a valid JSON file
    """
    SilouettesConfig(test_config.as_posix())


def test_config_missing_value(test_data_dir):
    """
    Test that Config class raises a ValueError when a required parameter is missing.
    """
    with pytest.raises(ValueError) as excinfo:
        SilouettesConfig(
            test_data_dir.joinpath("configs", "bad_config_missing.json").as_posix()
        )
        assert excinfo.value.message == "ValueError: name is missing from input."


def test_config_bad_dtype(test_data_dir):
    """
    Test that Config class raises a TypeError when a required parameter is the wrong
    dtype.
    """
    with pytest.raises(TypeError) as excinfo:
        SilouettesConfig(
            test_data_dir.joinpath("configs", "bad_config_dtype.json").as_posix()
        )
        assert excinfo.value.message == (
            "Invalid input for hub_height_m: must be type <class 'numbers.Number'>"
        )


def test_config_bad_baseparams(test_data_dir):
    """
    Test that Config class raises a TypeError when a dictionary is not provided
    for a BaseParameter attribute.
    """
    with pytest.raises(TypeError) as excinfo:
        SilouettesConfig(
            test_data_dir.joinpath("configs", "bad_config_baseparams.json").as_posix()
        )
        assert excinfo.value.message == (
            "Invalid input for <class 'via_wind.config.TurbineParams'>: "
            "must be a dictionary/mapping."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
