# -*- coding: utf-8 -*-
"""
image module
"""
from imageio.v3 import imread


def mean_image_intensity(image_path):
    """
    Calculate the aggregate/mean intensity of a black and white image, such that
    an image that was totally black would have an intensity of 1 and an image that
    was totally white would have an intensity of 0. This value can also be interpreted
    as the percent of the field of view of the image that is non-white, accounting
    for the intensity of different shades of gray (darker = more intense).

    Parameters
    ----------
    image_path : [pathlib.Path, str]
        Path to image to analyze. Expected to be a black and white image.

    Returns
    -------
    float
        Mean image intensity on scale from 0 to 1. May also be interpreted as the
        ratio of the field of view of the image that is non-white.

    Raises
    -------
        A TypeError will be raised if the input image does not appear to be black and
        white.
    """

    image_array = imread(image_path)
    if image_array.ndim != 2:
        raise TypeError(
            "Invalid input image: contains multiple bands/channels. "
            "Input image must be black and white (single band)."
        )

    # rescale so that black = 1 and white = 0, with gray in between
    # (darker gray closer to 1)
    intensity = (255 - image_array) / 255

    mean_intensity = intensity.mean()

    return mean_intensity
