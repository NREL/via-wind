# -*- coding: utf-8 -*-
"""Unit tests for via_wind.image module"""
import math

import pytest

from via_wind import image


def test_mean_image_intensity_math(test_data_dir):
    """
    Unit test for mean_image_intensity function to verify that it produces the
    expected image intensity values when passed known images that are e.g., entirely
    black, entirely white, 50%, 25%, etc.
    """

    image_paths = test_data_dir.joinpath("intensity_images").glob("*.png")
    for image_path in image_paths:
        intensity = float(image_path.name.replace(".png", "")) / 100
        assert math.isclose(
            image.mean_image_intensity(image_path), intensity, abs_tol=1e-2
        )


def test_mean_image_intensity_rgb(test_data_dir):
    """
    See what happens when mean_image_intensity function is passed an RGB image
    """
    image_path = test_data_dir.joinpath("intensity_images", "rgb", "cyan.png")
    with pytest.raises(TypeError) as excinfo:
        image.mean_image_intensity(image_path)
        assert excinfo.value.message.startswith(
            "Invalid input image: contains multiple bands/channels."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
