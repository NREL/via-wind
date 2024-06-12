# -*- coding: utf-8 -*-
"""
measures module
"""
from numbers import Number

import numpy as np


def calc_distance_and_direction(shape):
    """
    For an array of the specified shape, calculates the distance and direction from the
    center point to each cell in the array. Returns separate arrays for distance
    and direction. Distance is in units of cells, direction is in units of degrees
    clockwise from due north / up.

    Parameters
    ----------
    shape : tuple
        2D tuples specifying the array shape.

    Returns
    -------
    tuple
        Returns a tuple of two numpy.ndarrays, where the first array is the distance
        array and the second is the direciton array.
    """

    n_rows, n_cols = shape

    if n_rows // 2 == n_rows / 2:
        # even
        center_y = (n_rows - 1) / 2
    else:
        # odd
        center_y = n_rows // 2

    if n_cols // 2 == n_cols / 2:
        # even
        center_x = (n_cols - 1) / 2
    else:
        center_x = n_cols // 2

    center = (center_y, center_x)

    # create grids for the horizontal and vertical distance to the center
    grid_x, grid_y = np.mgrid[0 : shape[0], 0 : shape[1]].astype(float)
    grid_x -= center[0]
    grid_y -= center[1]

    # calculat the euclidean distances to the center
    distance = np.hypot(grid_x, grid_y)

    # calculate the euclidean direction to the center
    # adding np.pi/2 and fixing negatives sets this to be [0, 360) clockwise from North
    direction = np.degrees(np.arctan2(grid_x, grid_y) + np.pi / 2)
    direction[direction < 0] = direction[direction < 0] + 360

    return distance, direction


def calc_lookangle(direction_from_turbine, turbine_bearing):
    """
    Calculate the horizontal "lookangle" between a viewer location and a turbine,
    accounting for the direction of the viewer from the turbine and the turbine's
    orientation/bearing.

    Parameters
    ----------
    direction_from_turbine : [numpy.ndarray, float]
        Direction of the viewer's location from the turbine in units of degrees
        clockwise from north (e.g., 90 degrees = due east, 180 degrees = due south,
        etc.).
    turbine_bearing : float
        Angular bearing of the direction the turbine is facing, in units of degrees
        clockwise from north. In an overhead view, the direction the turbine is facing
        can be determined by drawing a straight line following the nacelle to the hub.
        The rotor will be perpendicular to this bearing.

    Returns
    -------
    numpy.ndarray
        Return a numpy float array with the horizontal look angle for each input in
        the input direction_from_turbine. If the input is an array, the size and shape
        of this output array will match. If the input is a float, the output array will
        have one element.
    """

    direction_from_turbine_rad = np.radians(direction_from_turbine)
    udir = np.sin(np.array(direction_from_turbine_rad))
    vdir = np.cos(np.array(direction_from_turbine_rad))
    vector_dir = np.array([udir.ravel(), vdir.ravel()])

    turbine_bearing_rad = np.radians(turbine_bearing)
    uturb = np.sin(turbine_bearing_rad)
    vturb = np.cos(turbine_bearing_rad)
    vector_turb = np.array([uturb, vturb])

    # cast dot product to float32 to avoid very rare floating point errors
    # that push this out of range
    dot = np.arccos(np.dot(vector_dir.T, vector_turb).astype("float32"))
    dot_degrees = np.degrees(dot)

    if isinstance(direction_from_turbine, Number):
        return dot_degrees

    return dot_degrees.reshape(direction_from_turbine.shape)


def classify_look_angle(direction_from_turbine, turbine_bearing):
    """
    Classify the look angle towards a turbine into categories (1=FRONT, 2=DIAGONAL, or
    3=SIDE) based on the direction from the turbine to the viewer's location and the
    orientation of the turbine.

    Parameters
    ----------
    direction_from_turbine : [numpy.ndarray, float]
        Direction of the viewer's location from the turbine in units of degrees
        clockwise from north (e.g., 90 degrees = due east, 180 degrees = due south,
        etc.).
    turbine_bearing : float
        Angular bearing of the direction the turbine is facing, in units of degrees
        clockwise from north. In an overhead view, the direction the turbine is facing
        can be determined by drawing a straight line following the nacelle to the hub.
        The rotor will be perpendicular to this bearing.

    Returns
    -------
    numpy.ndarray
        Return a numpy integer array with the following values: 1 (="FRONT"),
        2 (="DIAGONAL"), 3 (="SIDE"), and -1 (="UNKNOWN"). If the input
        direction_from_turbine is an array, the size and shape of this output
        array will match. If the input is a float, the output array will have one
        element.
    """

    lookangle = calc_lookangle(direction_from_turbine, turbine_bearing)
    lookangle[lookangle > 90] = 180 - lookangle[lookangle > 90]

    # classes: 1 = Front, 2 = Diagonal, 3 = Side, -1 = error
    look_class = np.where(
        (lookangle >= 0) & (lookangle < 22.5),
        1,
        np.where(
            (lookangle >= 22.5) & (lookangle <= 67.5),
            2,
            np.where((lookangle > 67.5) & (lookangle <= 90), 3, -1),
        ),
    )
    if -1 in look_class:
        raise ValueError(
            "Some lookangles could not be classified for turbine_bearing "
            f"{turbine_bearing}"
        )

    return look_class
