# -*- coding: utf-8 -*-
"""Unit tests for via_wind.cli.fov module"""
import pytest

from via_wind.cli.fov import _parse_silouette_directories

# note: only includes tests for _parse_silouette_directories. all other functionality
# is tested through cli.test_cli.test_fov_happy


def test_parse_silouette_directories_happy(test_data_dir):
    """
    Happy path test for _parse_silouette_directories - test that it is able to parse
    the three different types of expected inputs and return the correct number of
    paths for each one.
    """
    options = []
    # 1 - Single folder path
    options.append(test_data_dir.joinpath("silouette_outputs", "test").as_posix())
    # 2 - List of folder paths
    options.append([test_data_dir.joinpath("silouette_outputs", "test").as_posix()])
    # 3 - Path to parent folder
    options.append(test_data_dir.joinpath("silouette_outputs", "*").as_posix())
    expected_lengths = [1, 1, 1]
    for sil_config_option, expected_length in zip(options, expected_lengths):
        result = _parse_silouette_directories(sil_config_option)
        assert len(result) == expected_length, "Result does not match expected length"


def test_parse_silouette_directories_type_error_folder(test_data_dir):
    """
    Unit test for _parse_silouette_directories - test that it raises TypeError with
    expected message when passed a file as input.
    """
    with pytest.raises(TypeError, match="Invalid input*"):
        silouette_directories = test_data_dir.joinpath(
            "silouette_outputs", "test", "config.json"
        )
        _parse_silouette_directories(silouette_directories.as_posix())


def test_parse_silouette_directories_type_error_int():
    """
    Unit test for _parse_silouette_directories - test that it raises TypeError with
    expected message when passed an input that is not a list or str.
    """
    with pytest.raises(TypeError, match="Invalid type*"):
        _parse_silouette_directories(1)


def test_parse_silouette_directories_not_found_file(test_data_dir):
    """
    Unit test for _parse_silouette_directories - test that it raises a FileNotFoundError
    with expected message when passed an input file that does not exist.
    """
    with pytest.raises(FileNotFoundError, match="Could not find folder*"):
        _parse_silouette_directories(test_data_dir.joinpath("x").as_posix())


def test_parse_silouette_directories_not_found_pattern(test_data_dir):
    """
    Unit test for _parse_silouette_directories - test that it raises a FileNotFoundError
    with expected message when passed an input folder pattern that does contain
    any subdirectories.
    """
    with pytest.raises(FileNotFoundError, match="Could not find any subdirectories*"):
        _parse_silouette_directories(
            test_data_dir.joinpath("silouette_outputs", "test", "*").as_posix()
        )


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
