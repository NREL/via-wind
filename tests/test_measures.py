# -*- coding: utf-8 -*-
"""Unit tests for via_wind.measures module"""
import math

import pytest
import numpy as np

from via_wind import measures


def test_calc_distance_and_direction_symmetric_square():
    """
    Unit tests for calc_distance_and_direction under the most common and simplest
    case where the input shape is square and has a center pixel (i.e., has an odd
    number of rows and columns)
    """

    shapes = [(101, 101), (25, 25), (3, 3)]
    for shape in shapes:
        distance, direction = measures.calc_distance_and_direction(shape)

        assert direction[0, shape[1] // 2] == 0
        # due west
        assert direction[shape[0] // 2, 0] == 270
        # due east
        assert direction[shape[0] // 2, -1] == 90
        # due south
        assert direction[-1, shape[1] // 2] == 180
        # northeast
        assert direction[0, -1] == 45
        # southeast
        assert direction[-1, -1] == 135
        # southwest
        assert direction[-1, 0] == 225
        # northwest
        assert direction[0, 0] == 315

        assert distance[0, shape[1] // 2] == shape[0] // 2
        # due west
        assert distance[shape[0] // 2, 0] == shape[1] // 2
        # due east
        assert distance[shape[0] // 2, -1] == shape[1] // 2
        # due south
        assert distance[-1, shape[1] // 2] == shape[0] // 2


def test_calc_distance_and_direction_nonsymmetric_square():
    """
    Unit tests for calc_distance_and_direction under the case where the input shape is
    square, but does not have a center pixel (i.e., has an even number of rows and
    columns)
    """

    shapes = [(100, 100), (24, 24), (4, 4)]
    for shape in shapes:
        distance, direction = measures.calc_distance_and_direction(shape)

        # check direction
        # northeast
        assert direction[0, -1] == 45
        # southeast
        assert direction[-1, -1] == 135
        # southwest
        assert direction[-1, 0] == 225
        # northwest
        assert direction[0, 0] == 315

        # check distance
        # due north
        assert math.isclose(
            distance[0, shape[1] // 2], shape[0] / 2 - 0.5, abs_tol=1e-1
        )
        # due west
        assert math.isclose(
            distance[shape[0] // 2, 0], shape[1] / 2 - 0.5, abs_tol=1e-1
        )
        # due east
        assert math.isclose(
            distance[shape[0] // 2, -1], shape[1] / 2 - 0.5, abs_tol=1e-1
        )
        # due south
        assert math.isclose(
            distance[-1, shape[1] // 2], shape[0] / 2 - 0.5, abs_tol=1e-1
        )


def test_calc_distance_and_direction_any_shape():
    """
    Unit tests for calc_distance_and_direction for a variety of shapes.
    """

    shapes = [(500, 101), (10, 100), (4, 6)]
    for shape in shapes:
        distance, direction = measures.calc_distance_and_direction(shape)

        # check direction
        # northeast
        assert math.isclose(
            direction[0, -1],
            np.degrees(np.arctan2(shape[1] / 2 - 0.5, shape[0] / 2 - 0.5)),
            abs_tol=1e-3,
        )
        # southeast
        assert math.isclose(
            direction[-1, -1],
            np.degrees(np.arctan2(-(shape[1] / 2 - 0.5), shape[0] / 2 - 0.5)) + 180,
            abs_tol=1e-3,
        )
        # southwest
        assert math.isclose(
            direction[-1, 0],
            np.degrees(np.arctan2(-(shape[1] / 2 - 0.5), -(shape[0] / 2 - 0.5))) + 360,
            abs_tol=1e-3,
        )
        # northwest
        assert math.isclose(
            direction[0, 0],
            np.degrees(np.arctan2(shape[1] / 2 - 0.5, -(shape[0] / 2 - 0.5))) + 180,
            abs_tol=1e-3,
        )

        # check distance
        # due north
        assert math.isclose(
            distance[0, shape[1] // 2], shape[0] / 2 - 0.5, abs_tol=1e-1
        )
        # due west
        assert math.isclose(
            distance[shape[0] // 2, 0], shape[1] / 2 - 0.5, abs_tol=1e-1
        )
        # due east
        assert math.isclose(
            distance[shape[0] // 2, -1], shape[1] / 2 - 0.5, abs_tol=1e-1
        )
        # due south
        assert math.isclose(
            distance[-1, shape[1] // 2], shape[0] / 2 - 0.5, abs_tol=1e-1
        )


def test_calc_lookangle_floats():
    """
    Unit test for calc_lookangle() running with float inputs. Tests various
    combinations of inputs produce corresponding expected outputs.
    """

    test_values = [
        (270, 0, 90),
        (0, 0, 0),
        (90, 0, 90),
        (135, 0, 135),
        (0, 180, 180),
        (360, 360, 0),
        (360, 0, 0),
        (450, 0, 90),
        (450, 450, 0),
    ]

    for direction_from_turbine, turbine_bearing, lookangle in test_values:
        result = measures.calc_lookangle(
            direction_from_turbine=direction_from_turbine,
            turbine_bearing=turbine_bearing,
        )
        assert np.isclose(result, np.array(lookangle), atol=1e-3).all()


def test_calc_lookangle_array():
    """
    Unit test for calc_lookangle() running with single value array inputs. Tests various
    combinations of inputs produce corresponding expected outputs.
    """

    test_values = [
        (45, 90, 45),
        (30, 120, 90),
        (90, 270, 180),
        (215, 30, 175),
        (360, 360, 0),
        (360, 0, 0),
        (450, 0, 90),
        (450, 450, 0),
    ]

    shape = (101, 101)

    direction_from_turbine = np.zeros(shape)
    lookangle = np.zeros(shape)

    for direction_from_turbine_val, turbine_bearing, lookangle_val in test_values:
        direction_from_turbine[:] = direction_from_turbine_val
        lookangle[:] = lookangle_val
        result = measures.calc_lookangle(
            direction_from_turbine=direction_from_turbine,
            turbine_bearing=turbine_bearing,
        )
        assert np.isclose(result, lookangle, atol=1e-3).all()


def test_calc_lookangle_multivalue_array():
    """
    Unit test for calc_lookangle() running with multiple value array input. Ensures
    pixel wise results are correct
    """

    shape = (10, 10)
    turbine_bearing = 0
    test_values = [
        (45, 45),
        (75, 75),
        (120, 120),
        (345, 15),
        (270, 90),
        (185, 175),
        (15, 15),
        (355, 5),
        (360, 0),
        (415, 55),
    ]

    direction_from_turbine = np.zeros(shape)
    lookangle = np.zeros(shape)

    for i, values in enumerate(test_values):
        direction_from_turbine_val, lookangle_val = values
        direction_from_turbine[i, :] = direction_from_turbine_val
        lookangle[i, :] = lookangle_val

    result = measures.calc_lookangle(
        direction_from_turbine=direction_from_turbine, turbine_bearing=turbine_bearing
    )
    assert np.isclose(result, lookangle, atol=1e-3).all()


def test_classify_lookangle_floats():
    """
    Tests classify lookangle floats produces expected values when inputs are floats
    """

    turbine_bearings = [0, 90, 225, 315]
    directions_from_turbine = [0, 45, 90, 135, 180, 225, 270, 315]

    expected_results = [
        # turbine bearing = 0
        "FRONT",
        "DIAGONAL",
        "SIDE",
        "DIAGONAL",
        "FRONT",
        "DIAGONAL",
        "SIDE",
        "DIAGONAL",
        # turbine bearing = 90
        "SIDE",
        "DIAGONAL",
        "FRONT",
        "DIAGONAL",
        "SIDE",
        "DIAGONAL",
        "FRONT",
        "DIAGONAL",
        # turbine bearing = 225
        "DIAGONAL",
        "FRONT",
        "DIAGONAL",
        "SIDE",
        "DIAGONAL",
        "FRONT",
        "DIAGONAL",
        "SIDE",
        # turbine bearing = 315
        "DIAGONAL",
        "SIDE",
        "DIAGONAL",
        "FRONT",
        "DIAGONAL",
        "SIDE",
        "DIAGONAL",
        "FRONT",
    ]

    lookangles = {1: "FRONT", 2: "DIAGONAL", 3: "SIDE", -1: "UNKNOWN"}

    i = 0
    for turbine_bearing in turbine_bearings:
        for direction_from_turbine in directions_from_turbine:
            result = measures.classify_look_angle(
                direction_from_turbine=direction_from_turbine,
                turbine_bearing=turbine_bearing,
            )
            view = lookangles[result[0]]
            assert view == expected_results[i]
            i += 1


def test_classify_lookangle_array():
    """
    Tests classify lookangle floats produces expected values when input includes an
    array.
    """

    turbine_bearing = 90
    directions_from_turbine_values = [0, 45, 90, 135, 180, 225, 270, 315]
    expected_result_values = [3, 2, 1, 2, 3, 2, 1, 2]
    shape = (len(directions_from_turbine_values), len(directions_from_turbine_values))

    direction_from_turbine = np.zeros(shape)
    expected_result = np.zeros(shape, dtype="int")
    for i, value in enumerate(directions_from_turbine_values):
        direction_from_turbine[:, i] = value
        expected_result[:, i] = expected_result_values[i]

    result = measures.classify_look_angle(
        direction_from_turbine=direction_from_turbine, turbine_bearing=turbine_bearing
    )
    assert (result == expected_result).all()


def test_calc_lookangle_floating_point_error():
    """
    Unit test for rare case where calc_lookangle() used to produce nans because
    of floating point precision issues in the dot product result.
    """

    assert np.array_equal(measures.calc_lookangle(225, 225), np.array([0]))


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
