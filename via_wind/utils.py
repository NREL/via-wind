# -*- coding: utf-8 -*-
"""
utils module
"""
import datetime
import time
from pathlib import Path


def verify_directory(directory):
    """
    Check that the input directory path exists and is a folder.

    Parameters
    ----------
    directory : str
        Path to directory.

    Raises
    ------
    FileNotFoundError
        A FileNotFoundError will be raised if the input path does not exist.
    TypeError
        A TypeError will be raised if the input path is not a folder.
    """
    if Path(directory).exists() is False:
        raise FileNotFoundError(f"Input directory {directory} could not be found.")
    if Path(directory).is_dir() is False:
        raise TypeError(f"Input directory {directory} is not a folder.")


def verify_file(fpath):
    """
    Check that the input file path exists and is a file.

    Parameters
    ----------
    fpath : str
        Path to file.

    Raises
    ------
    FileNotFoundError
        A FileNotFoundError will be raised if the input path does not exist.
    TypeError
        A TypeError will be raised if the input path is not a file.
    """
    if Path(fpath).exists() is False:
        raise FileNotFoundError(f"Input fpath {fpath} could not be found.")
    if Path(fpath).is_dir() is True:
        raise TypeError(f"Input fpath {fpath} is not a file.")
