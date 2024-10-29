# -*- coding: utf-8 -*-
"""Unit tests for via_wind.utils module"""
import pytest

from via_wind.utils import verify_directory, verify_file


def test_verify_directory_happy(test_data_dir):
    """
    Happy path test for verify_directory - test that it does not raise an error when an
    existing folder is passed as input.
    """
    verify_directory(test_data_dir.as_posix())


def test_verify_directory_error_file(test_config):
    """
    Unit test for verify_directory - test that it raises TypeError with expected message
    when passed a file as input.
    """
    input_directory = test_config.as_posix()
    with pytest.raises(
        TypeError,
        match=f"Input directory {input_directory} is not a folder",
    ):
        verify_directory(input_directory)


def test_verify_viewsheds_directory_not_found(test_data_dir):
    """
    Unit test for verify_directory - test that it raises FileNotFoundError when the
    input folder does not exist.
    """
    input_directory = test_data_dir.as_posix() + "x"
    with pytest.raises(
        FileNotFoundError,
        match=f"Input directory {input_directory} could not be found",
    ):
        verify_directory(input_directory)


def test_verify_file_happy(test_config):
    """
    Happy path test for verify_file - test that it does not raise an error when an
    existing folder is passed as input.
    """
    verify_file(test_config.as_posix())


def test_verify_file_error_file(test_data_dir):
    """
    Unit test for verify_file - test that it raises TypeError with expected message when
    passed a folder as input.
    """
    input_file = test_data_dir.as_posix()
    with pytest.raises(
        TypeError,
        match=f"Input fpath {input_file} is not a file",
    ):
        verify_file(input_file)


def test_verify_viewsheds_file_not_found(test_config):
    """
    Unit test for verify_file - test that it raises FileNotFoundError
    when the input file does not exist.
    """
    input_file = test_config.as_posix() + "x"
    with pytest.raises(
        FileNotFoundError,
        match=f"Input fpath {input_file} could not be found",
    ):
        verify_file(input_file)


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
