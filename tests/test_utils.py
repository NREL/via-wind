# -*- coding: utf-8 -*-
"""Unit tests for via_wind.utils module"""
import pytest

from via_wind.utils import hms, ProgressTracker, verify_directory, verify_file


def test_hms():
    """
    Unit test for hms() function - checks that output strings are correct for known
    inputs.
    """

    test_values = [
        (15, "0:00:15"),
        (60, "0:01:00"),
        (119, "0:01:59"),
        (3601, "1:00:01"),
        (36061, "10:01:01"),
        (86401, "1 day, 0:00:01"),
    ]
    for seconds, expected_results in test_values:
        assert hms(seconds) == expected_results


def test_progress_tracker():
    """
    Very basic unit test for Progress Tracker class. Tests that it produces messages
    for each update that start and end as expected.
    """

    n_iters = 10
    messages = []
    with ProgressTracker(total=n_iters, desc="Progress so far") as p:
        for _ in range(0, 10):
            messages.append(p.message)
            p.update(1)

    assert len(messages) == n_iters
    for i, message in enumerate(messages):
        assert message.startswith(f"Progress so far {i+1}/{n_iters}")
        assert message.endswith("/it]")


def test_progress_tracker_exception():
    """
    Unit test for Progress Tracker class. Tests that if an exception occurs, it
    is raised.
    """

    with pytest.raises(ValueError, match="This is a test"):
        with ProgressTracker(total=1, desc="Progress so far"):
            raise ValueError("This is a test")


def test_verify_directory_happy(test_data_dir):
    """
    Happy path test for verify_directory - test that it does not raise an
    error when an existing folder is passed as input
    """
    verify_directory(test_data_dir.as_posix())


def test_verify_directory_error_file(test_config):
    """
    Unit test for verify_directory - test that it raises TypeError with
    expected message when passed a file as input.
    """
    input_directory = test_config.as_posix()
    with pytest.raises(
        TypeError,
        match=f"Input directory {input_directory} is not a folder",
    ):
        verify_directory(input_directory)


def test_verify_viewsheds_directory_not_found(test_data_dir):
    """
    Unit test for verify_directory - test that it raises FileNotFoundError
    when the input folder does not exist.
    """
    input_directory = test_data_dir.as_posix() + "x"
    with pytest.raises(
        FileNotFoundError,
        match=f"Input directory {input_directory} could not be found",
    ):
        verify_directory(input_directory)


def test_verify_file_happy(test_config):
    """
    Happy path test for verify_file - test that it does not raise an
    error when an existing folder is passed as input
    """
    verify_file(test_config.as_posix())


def test_verify_file_error_file(test_data_dir):
    """
    Unit test for verify_file - test that it raises TypeError with
    expected message when passed a folder as input.
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
