# -*- coding: utf-8 -*-
"""Unit tests for via_wind.cli.silouettes module"""
import pytest

from via_wind.cli.silouettes import _parse_silouette_configs

# note: only includes tests for _parse_silouette_configs. all other functionality
# is tested through cli.test_cli.test_silouettes_happy


def test_parse_silouette_configs_happy(test_data_dir, test_config):
    """
    Happy path test for _parse_silouette_configs - test that it is able to parse the
    three different types of expected inputs and return the correct number of paths for
    each one.
    """
    options = []
    # 1 - Search Pattern string as input
    options.append(test_data_dir.joinpath("configs", "*.json").as_posix())
    # 2 - Single file path string
    options.append(test_config.as_posix())
    # 3 - List of file paths
    options.append(
        [f.as_posix() for f in test_data_dir.joinpath("configs").glob("*.json")]
    )
    expected_lengths = [3, 1, 3]
    for sil_config_option, expected_length in zip(options, expected_lengths):
        result = _parse_silouette_configs(sil_config_option)
        assert len(result) == expected_length, "Result does not match expected length"


def test_parse_silouette_configs_type_error_folder(test_data_dir):
    """
    Unit test for _parse_silouette_configs - test that it raises TypeError with expected
    message when passed a folder as input.
    """
    with pytest.raises(TypeError, match="Invalid input*"):
        _parse_silouette_configs(test_data_dir.as_posix())


def test_parse_silouette_configs_type_error_int():
    """
    Unit test for _parse_silouette_configs - test that it raises TypeError with expected
    message when passed an input that is not a list or str.
    """
    with pytest.raises(TypeError, match="Invalid type*"):
        _parse_silouette_configs(1)


def test_parse_silouette_configs_not_found_file(test_config):
    """
    Unit test for _parse_silouette_configs - test that it raises a FileNotFoundError
    with expected message when passed an input file that does not exist.
    """
    with pytest.raises(FileNotFoundError, match="Could not find file*"):
        _parse_silouette_configs(test_config.as_posix() + "x")


def test_parse_silouette_configs_not_found_pattern(test_data_dir):
    """
    Unit test for _parse_silouette_configs - test that it raises a FileNotFoundError
    with expected message when passed an input file pattern that does not match any
    files.
    """
    with pytest.raises(FileNotFoundError, match="Could not find any files*"):
        _parse_silouette_configs(
            test_data_dir.joinpath("configs").joinpath("*.yaml").as_posix()
        )


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
