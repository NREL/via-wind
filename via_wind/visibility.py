# -*- coding: utf-8 -*-
"""
visibility module
"""
import itertools

import pandas as pd
from pandas.api.types import is_numeric_dtype, is_string_dtype, is_integer_dtype
import numpy as np
from osgeo import gdal

# need this to keep gdal from issuing warnings
gdal.UseExceptions()

REQUIRED_TURBINE_COLS = {
    "gid": (is_integer_dtype, "must be integer"),
    "rd_m": (is_numeric_dtype, "must be numeric"),
    "hh_m": (is_numeric_dtype, "must be numeric"),
    "geometry": (
        lambda x: x.geom_type.unique().tolist() == ["Point"],
        "must have Point geometry type",
    ),
}

REQUIRED_FOV_COLS = {
    "hub_height_m": (is_numeric_dtype, "must be numeric"),
    "rotor_diameter_m": (is_numeric_dtype, "must be numeric"),
    "distance_m": (is_numeric_dtype, "must be numeric"),
    "rotation": (is_string_dtype, "must be numeric"),
    "obstruction_height_m": (is_numeric_dtype, "must be numeric"),
}

TURBINE_ROTATIONS = {"FRONT": 1, "DIAGONAL": 2, "SIDE": 3}

NOT_VISIBLE_VALUE = 58368


def calc_viewshed_shape(max_distance_km, elev_resolution_m):
    """
    Determine the shape of a viewshed raster based on the maximum analysis distance
    and the raster resolution.

    Parameters
    ----------
    max_distance_km : float
        Maximum analysis distance for the viewshed analysis in linear units of
        kilometers.
    resolution_m : float
        Resolution of the elevation data to be used in the viewshed analysis.

    Returns
    -------
    tuple
        Returns a tuple of the format (int, int) describing the shape (rows, columns)
        of the viewshed raster that will be produced given the input parameters.
    """
    width = int(np.ceil((max_distance_km * 1000) / elev_resolution_m) * 2 + 1)

    return (width, width)


def run_viewshed(
    elevation_src, turbine_x, turbine_y, turbine_z, max_distance, viewer_z
):
    """
    Runs the gdal_viewshed() function on the input elevation data.

    Parameters
    ----------
    elevation_src : str
        Path to elevation raster dataset.
    turbine_x : float
        X coordinate of the turbine location. Must be in the CRS of the elevation
        dataset.
    turbine_y : float
        Y coordinate of the turbine location. Must be in the CRS of the elevation
        dataset.
    turbine_z : float
        Height of the turbine or turbine section from which visibility will be analyzed.
        Must be in the units corresponding to the linear units of elevation  dataset
        CRS.
    max_distance : float
        Maximum distance from the turbine for which visibility will be analyzed. Must be
        in the units corresponding to the linear units of elevation  dataset CRS.
    viewer_z : float
        Height of the viewer/observers above ground. Must be in the units corresponding
        to the linear units of elevation dataset CRS.

    Returns
    -------
    osgeo.gdal.Dataset
        GDAL Dataset containing results of the viewshed analysis.
    """
    src_ds = gdal.Open(elevation_src)
    viewshed = gdal.ViewshedGenerate(
        srcBand=src_ds.GetRasterBand(1),
        driverName="MEM",
        targetRasterName="",
        creationOptions=[],
        observerX=turbine_x,
        observerY=turbine_y,
        observerHeight=turbine_z,
        targetHeight=viewer_z,
        visibleVal=1,
        invisibleVal=0,
        outOfRangeVal=0,
        noDataVal=0,
        dfCurvCoeff=6 / 7,
        mode=gdal.GVM_Edge,
        maxDistance=max_distance,
        heightMode=gdal.GVOT_NORMAL,
    )

    return viewshed


def check_columns(df, required_columns):
    """
    Check an input dataframe has the required columns and pass

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame to check
    required_columns : dict
        Dictionary defining the columns to required columns and their validity check.
        Keys should be column names and the value for each should be a function that
        can be called against the dataframe column to check its validity.

    Raises
    ------
    KeyError
        A KeyError will be raised if one of the required columns is missing.
    ValueError
        A ValueError will be raised if one of the required column checks does not pass.
    """
    for col in required_columns:
        dtype_checker, dtype_msg = required_columns[col]
        if col not in df.columns:
            raise KeyError(f"Required column {col} not found in dataframe")
        if not dtype_checker(df[col]):
            raise ValueError(f"Invalid values for column {col}: {dtype_msg}")


def get_obstruction_heights(rotor_diameter, hub_height, obstruction_interval):
    """
    Get obstruction heights based on turbine dimensions and the obstruction interval.
    Obstruction heights will start from the max tip height of the turbine and range
    down to the ground at the specified increment. Values are returned in ascending
    order.

    Parameters
    ----------
    rotor_diameter : float
        Turbine rotor diameter. Must be in the same units as the other inputs.
    hub_height : float
        Turbine hub height. Must be in the same units as the other inputs.
    obstruction_interval : float
        Obstruction height interval. Must be in the same units as the other inputs.

    Returns
    -------
    list
        List of obstruction heights (in ascending order)
    """
    max_tip_height = hub_height + rotor_diameter * 0.5
    obstruction_heights = np.arange(
        0, max_tip_height + obstruction_interval, obstruction_interval
    ).tolist()

    return obstruction_heights


def check_fov_lkup_complete(
    fov_df,
    turbines_df,
    obstruction_interval_m,
    max_distance_km,
    turbine_rotations=None,
):
    """
    Checks that a field-of-view lookup dataframe has all of the required records
    based on the dimensions of the input turbines, the obstruction height interval,
    the max distance to be analyzed, and the turbine rotations to be used.

    Parameters
    ----------
    fov_df : pandas.DataFrame
        DataFrame containing percent field-of-view lookup values.
    turbines_df : pandas.DataFrame
        DataFrame containing turbine locations.
    obstruction_interval_m : float
        Obstruction height interval. Must be in the same units as the other inputs.
    max_distance_km : float
        Maximum distance from the turbine for which visibility will be analyzed, in
        units of kilometers.
    turbine_rotations : list, optional
        List of turbine rotations required. If not specified, will default to keys of
        TURBINE_ROTATIONS.

    Raises
    ------
    ValueError
        A ValueError will be raised if any of the required records are not present
        in the fov dataframe.
    """

    if turbine_rotations is None:
        turbine_rotations = list(TURBINE_ROTATIONS.keys())

    required_turbine_dimensions = np.unique(
        turbines_df[["rd_m", "hh_m"]].to_numpy(), axis=0
    ).tolist()
    required_records = []

    # make sure that the FOV lookup table contains distances ranging out close to the
    # maximum analysis distances
    max_fov_distance_km = fov_df["distance_m"].max() / 1000
    if max_fov_distance_km < max_distance_km:
        raise ValueError(
            "Maximum distance in FOV lookup table is smaller than the maximum distance "
            "from the turbine for which visibility will be analyzed. This indicates "
            "the FOV lookup table will not provide sufficient coverage of viewshed "
            "results."
        )

    distances = [
        d for d in fov_df["distance_m"].unique() if (d / 1000) <= max_distance_km
    ]
    for rotor_diameter_m, hub_height_m in required_turbine_dimensions:
        obstruction_heights = get_obstruction_heights(
            rotor_diameter_m, hub_height_m, obstruction_interval_m
        )
        new_records = list(
            itertools.product(
                [rotor_diameter_m],
                [hub_height_m],
                obstruction_heights,
                distances,
                turbine_rotations,
            )
        )
        required_records.extend(new_records)

    required_df = pd.DataFrame(
        required_records,
        columns=[
            "rotor_diameter_m",
            "hub_height_m",
            "obstruction_height_m",
            "distance_m",
            "rotation",
        ],
    )

    join_df = pd.merge(
        required_df, fov_df, how="inner", on=required_df.columns.tolist()
    )

    if len(join_df) < len(required_df):
        raise ValueError(
            "Required values are missing from the FOV lookup table. "
            "Check that the input FOV Lookup contains an entry for each combination of "
            "rotor diameter, hub height, obstruction height, distance, and rotation "
            "based on the input turbines dataset, obstruction_interval_m, and "
            "max_distance_km."
        )


def lookup_fov_pct(
    fov_df,
    rotor_diameter_m,
    hub_height_m,
    obst_height_array,
    distance_bin_array,
    lookangle_array,
):
    """
    Derive the array with the percent field-of-view occupied by the turbine for each
    pixel based on the turbine dimensions, obstruction height, distance bin and look
    angle arrays.

    Parameters
    ----------
    fov_df : pandas.DataFrame
        DataFrame containing percent field-of-view lookup values.
    rotor_diameter_m : float
        Rotor diameter of the turbine being analyzed, in units of meters.
    hub_height_m : float
        Hub height of the turbine being analyzed, in units of meters.
    obst_height_array : numpy.ndarray
        Numpy array giving the minimum obstruction height at which the turbine is
        visible for each pixel.
    distance_bin_array : numpy.ndarray
        Numpy array giving the distance bin for each pixel from the turbine.
    lookangle_array : numpy.ndarray
        Numpy array giving the look angle category (i.e., 1, 2, 3) from each pixel
        to the turbine.

    Returns
    -------
    numpy.ndarray
        Returns a numpy array where each value defines  percent of the field-of-view
        that the turbine occupies for that pixel.
    """

    join_columns = ["obstruction_height_m", "distance_m", "rotation_class"]

    # filter the fov lookup table to just the rows for these turbine dimensions
    fov_sub_df = fov_df[
        (fov_df["rotor_diameter_m"] == rotor_diameter_m)
        & (fov_df["hub_height_m"] == hub_height_m)
    ].copy()

    # create mask for pixels that are visible
    visible_pixels = obst_height_array != NOT_VISIBLE_VALUE

    # find the combinations of obstruction height, distance bin, and lookangle
    # where the turbine is visible and convert into a dataframe
    combos = np.array(
        [
            obst_height_array[visible_pixels],
            distance_bin_array[visible_pixels],
            lookangle_array[visible_pixels],
        ]
    )
    combos_df = pd.DataFrame(combos.T, columns=join_columns)

    # lookup the fov values for the height/dist/angle combinations via a join
    combo_fov_lkup = pd.merge(combos_df, fov_sub_df, how="left", on=join_columns)

    # initialize the output fov percent array with zeros
    fov_pct = np.zeros(obst_height_array.shape)
    # apply values back to the fov_pct array for the visible pixels
    fov_pct[visible_pixels] = combo_fov_lkup["pct_fov"].tolist()

    return fov_pct


def bin_distances(fov_df, distance_array):
    """
    Given a euclidean distance array and FOV lookup table, this function bins the
    distance values in the array to the nearest distance interval included in the FOV
    table.

    Parameters
    ----------
    fov_df : pandas.DataFrame
        DataFrame containing FOV lookup.
    distance_array : numpy.ndarray
        Two dimensional array containing euclidean distances to the center pixel.

    Returns
    -------
    numpy.ndarray
        Two dimensional array, same shape as distance_array, where the distance values
        have been binned to the nearest distance interval at which there is an FOV
        value.
    """
    distance_values = fov_df["distance_m"].unique()
    distance_bins = distance_values[
        np.abs(distance_array - distance_values[:, None, None]).argmin(axis=0)
    ]

    return distance_bins
