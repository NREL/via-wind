# -*- coding: utf-8 -*-
"""Helper functions for tests"""

import imagehash
from PIL import Image
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal


def check_files_match(pattern, dir_1_path, dir_2_path):
    """
    Verify that the files in two folders match. Files are filtered by the specified
    pattern and the contents of the two folders are searched recursively. Only the
    names of the files and their relative paths within the fodlers are compared -
    contents of the files are not checked.

    Parameters
    ----------
    pattern : str
        File pattern used for filtering files in the specified folders.
    dir_1_path : pathlib.Path
        Path to the first directory.
    dir_2_path : pathlib.Path
        Path to the second directory.

    Returns
    -------
    tuple
        Returns a tuple with two elements: the first element is a boolean indicating
        whether the files in the two folders match and the second is a list of
        differences between the two folders (if applicable). If the files match, the
        list will be empty.
    """

    output_files = [f.relative_to(dir_1_path) for f in dir_1_path.rglob(pattern)]
    expected_output_files = [
        f.relative_to(dir_2_path) for f in dir_2_path.rglob(pattern)
    ]

    difference = list(
        set(output_files).symmetric_difference(set(expected_output_files))
    )
    if len(difference) == 0:
        return True, []

    return False, difference


def compare_images_approx(image_1_path, image_2_path, hash_size=12, max_diff_pct=0.25):
    """
    Check if two images match within a specified tolerance.

    Parameters
    ----------
    image_1_path : pathlib.Path
        File path to first image.
    image_2_path : pathlib.Path
        File path to first image.
    hash_size : int, optional
        Size of the image hashes that will be used for image comparison,
        by default 12. Increase to make the check more precise, decrease to
        make it more approximate.
    max_diff_pct : float, optional
        Tolerance for the amount of difference allowed, by default 0.25 (= 25%).
        Increase to allow for a larger delta between the image hashes, decrease
        to make the check stricter and require a smaller delta between the
        image hashes.

    Returns
    -------
    tuple
        Returns a tuple with two elements: the first element is a boolean indicating
        whether the two images match within the specified tolerance parameters. The
        second element is a float indicating the percent difference between the two
        images.
    """

    expected_hash = imagehash.phash(Image.open(image_1_path), hash_size=hash_size)
    out_hash = imagehash.phash(Image.open(image_2_path), hash_size=hash_size)

    max_diff_bits = int(np.ceil(hash_size * max_diff_pct))

    diff = expected_hash - out_hash
    matches = diff <= max_diff_bits
    pct_diff = float(diff) / hash_size

    return matches, pct_diff


def compare_csv_data(csv_1, csv_2, **kwargs):
    """
    Compares the contents of two CSVs to make sure they match. Uses
    pandas.testing.assert_frame_equal under the hood; **kwargs will be passed
    to this function.

    Parameters
    ----------
    csv_1 : [str, pathlib.Path]
        Path to first CSV.
    csv_2 : [str, pathlib.Path]
        Path to second CSV.

    Raises
    ------
    AssertionError
        An AssertionError will be raised if the contents of the two CSVs do not match.
    """

    df1 = pd.read_csv(csv_1)
    df2 = pd.read_csv(csv_2)

    assert_frame_equal(df1, df2, **kwargs)
