# -*- coding: utf-8 -*-
"""
viewshed module - sets up CLI for viewshed command using nrel-gaps
"""
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

import rasterio
from rasterio.transform import Affine
import tqdm
from gaps.cli import as_click_command, CLICommandFromFunction
import numpy as np
import pandas as pd
import geopandas as gpd
from pyogrio import read_info
import pyproj

from via_wind import __version__
from via_wind.log import init_logger
from via_wind.utils import verify_file
from via_wind import raster, visibility, measures

# stop to_crs() bugs
pyproj.network.set_network_enabled(active=False)

LOGGER = logging.getLogger(__name__)


def _split_turbines(turbines_fpath, nodes):
    """
    Determine the splitting strategy for the input turbines

    Parameters
    ----------
    turbines_fpath : str
        Path to turbines datasets
    nodes : int
        Number of nodes to be used for command execution

    Returns
    -------
    tuple
        Returns a two element tuple that defines the splits for the turbines.
        The first element is an int indicating the number of turbines that will be
        processed by each node. The second element is a list defining the row
        offset of the dataset from which each subset will be started.
    """

    turbines_info = read_info(turbines_fpath)
    turbines_count = turbines_info["features"]
    batch_size = int(np.ceil(turbines_count / nodes))
    skip_features = np.arange(0, turbines_count, batch_size).tolist()

    return (batch_size, skip_features)


def _log_inputs(config):
    """
    Emit log messages summarizing user inputs

    Parameters
    ----------
    config : dict
        Configuration dictionary
    """
    LOGGER.info("Viewshed rasters will be derived based on the folowing config: ")
    for k, v in config.items():
        if k.startswith("_") or k == "execution_control":
            continue
        LOGGER.info(f"\t{k}: {v}")
    nodes = len(config.get("_skip_features", [1]))
    batch_size = config.get("_batch_size")
    LOGGER.info(
        f"Viewsheds will be analyzed in parallel on {nodes} nodes in batches of "
        f"{batch_size} records."
    )


def _preprocessor(config, job_name, log_directory, verbose):
    """
    Preprocess user-input configuration.

    Parameters
    ----------
    config : dict
        User configuration file input as (nested) dict.
    job_name : str
        Name of `job being run. Derived from the name of the folder containing the
        user configuration file.
    verbose : bool
        Flag to signal ``DEBUG`` verbosity (``verbose=True``).

    Returns
    -------
    dict
        Configuration dictionary modified to include additional or augmented
        parameters.
    """
    init_logger(job_name, log_directory, module=__name__, verbose=verbose, stream=False)
    config["_log_directory"] = log_directory.as_posix()
    config["_verbose"] = verbose
    # use pop instead of get here because gaps only expected the nodes argument
    # when using project_points as the split key. otherwise, nodes are based on the
    # number of elements in skip_features, which we make equal to nodes via the
    # _split_turbines function
    nodes = config.get("execution_control", {}).pop("nodes", 1)
    verify_file(config["fov_lkup_fpath"])
    verify_file(config["elev_fpath"])
    batch_size, skip_features = _split_turbines(config["turbines_fpath"], nodes)
    config["_batch_size"] = batch_size
    config["_skip_features"] = skip_features
    config["_local"] = (
        config.get("execution_control", {}).get("option", "local") == "local"
    )
    _log_inputs(config)

    return config


def run(
    turbines_fpath,
    fov_lkup_fpath,
    elev_fpath,
    obstruction_interval_m,
    max_dist_km,
    viewer_height_m,
    out_dir,
    job_name,
    _log_directory,
    _verbose,
    save_all=False,
    max_workers=None,
    _skip_features=None,
    _batch_size=None,
):
    """
    Estimates the percent of the field-of-view (FOV) occupied by each turbine in the
    input turbines dataset from the vantage point of each pixel in the surrounding area,
    out to the maximum specified distance. Resulting output is a series of GeoTiff
    rasters, one for each turbine, where the pixel values indicate the percent FOV
    occupied by the corresponding turbine. Should be used for visual impact analysis
    of individual turbines or as a pre-processing step to the merge command.

    Parameters
    ----------
    turbines_fpath : str
        Path to input turbines dataset. Should be a GIS Vector format (e.g., GeoPackage,
        Shapefile, etc).
    fov_lkup_fpath : str
        FOV Lookup table CSV. Typically produced by the fov command.
    elev_fpath : _type_
        Path to raster dataset containing elevation values (i.e., DEM or DSM).
        Pixel values should indicate the height of the pixel in meters. Raster must be
        projected to a CRS with linear units of meters.
    obstruction_interval_m : float
        Defines the height interval at which obstructions will be analyzed, specified in
        units of meters. For example, a value of 20 would run viewsheds for a given wind
        turbine starting at the max tip height, at intervals of 20m down to the ground.
        For a turbine with 80m hub height and 80m rotor diameter, this would result in
        viewsheds at the following heights: [120, 100, 80, 60, 40, 20, 0]. This value
        should correspond to the obstruction height intervals used in your fov-lkup CSV.
    max_dist_km : float
        Distance limit for viewshed analysis. Locations farther than this distance away
        from turbines will not be analyzed. Should be specified in units of kilometers.
    viewer_height_m : int
        Defines the height of the viewer used in the viewshed analysis, specified in
        units of meters. This should correspond to the camera.height_m used in your
        silouettes config(s).
    out_dir : str
        Output folder to which simulated turbine silouettes will be saved. If the folder
        does not exist, it will be created. If the folder does exist, existing files may
        be overwritten.
    job_name : str
        Name of the job being run. This is typically a combination of the project
        directory, the command name, and a tag unique to a job.
    _log_directory : str
        Path to log output directory.
    _verbose : bool
        Flag to signal ``DEBUG`` verbosity (``verbose=True``).
    save_all : bool, optional
        Flag to control whether to save all intermediate outputs as well as final
        results, by default False.
    max_workers : [int, NoneType], optional
        Maximum number of workers to use for multiprocessing, by default None, which
        uses all available CPUs.
    _skip_features : int, optional
        Number of records of the input dataset to skip before starting to read records.
        NOTE: This is an internal-only argument that is generated dynamically based on
        the number of records in the dataset and the number of nodes to be used
        for processing. It is NOT a user input, and if provided in the input config,
        will be overwritten.
    _batch_size : int, optional
        Number of records of the input dataset to read, starting from
        record number = (_skip_features + 1). NOTE: This is an internal-only argument
        that is generated dynamically based on the number of records in the dataset and
        the number of nodes to be used for processing. It is NOT a user input, and if
        provided in the input config, will be overwritten.

    Raises
    ------
    ValueError
        A ValueError will be raised if required wind direction frequency columns
        are missing from the input turbines dataset.
    """

    # create dedicated logger with filehandler for just this subprocess
    logger = init_logger(
        job_name, _log_directory, module=__name__, verbose=_verbose, stream=False
    )

    logger.info(
        f"Starting processing to derive viewshed rasters for {_batch_size} turbines "
        f"starting at record {_skip_features}"
    )

    # create folder at the output path
    out_path = Path(out_dir).joinpath("viewsheds").expanduser()
    out_path.mkdir(exist_ok=True, parents=False)

    if _skip_features is not None and _batch_size is not None:
        turbines_df = gpd.read_file(
            turbines_fpath,
            max_features=_batch_size,
            skip_features=_skip_features,
            engine="pyogrio",
        )
    else:
        # process the full dataframe - this should never happen when running this
        # using the viewsheds_cmd
        turbines_df = gpd.read_file(turbines_fpath, engine="pyogrio")

    # determine the set of columns defining wind directions
    winddir_cols = [c for c in turbines_df.columns if c.startswith("freq_winddir_")]
    if len(winddir_cols) == 0:
        raise ValueError(
            "No columns found matching the expected format for wind direction "
            "frequencies: freq_winddir_###"
        )

    logger.info("Loading Field-of-View (FOV) Lookup table")
    fov_df = pd.read_csv(fov_lkup_fpath)
    visibility.check_columns(fov_df, visibility.REQUIRED_FOV_COLS)
    fov_df["rotation_class"] = fov_df["rotation"].map(visibility.TURBINE_ROTATIONS)

    logger.info("Checking FOV Lookup Table for completeness.")
    visibility.check_fov_lkup_complete(
        fov_df, turbines_df, obstruction_interval_m, max_dist_km
    )

    logger.info("Getting CRS and Resolution of Elevation Raster")
    elev_info = raster.get_raster_info(elev_fpath)
    crs = elev_info["crs"]
    resolution = elev_info["resolution"]
    raster.validate_crs_units(crs)

    logger.info("Projecting turbines to match elevation raster")
    turbines_df.to_crs(crs, inplace=True)

    # create distance and direction arrays
    logger.info("Creating Distance and Direction arrays")
    array_shape = visibility.calc_viewshed_shape(max_dist_km, resolution)
    distance_array, direction_array = measures.calc_distance_and_direction(array_shape)
    # convert distance values from units of pixels to meters and bin the distances to
    # the nearest distance interval at which we have FOV values
    distance_bin_array = visibility.bin_distances(fov_df, distance_array * resolution)

    futures = {}
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        for _, turbine in turbines_df.iterrows():
            future = pool.submit(
                viewshed,
                turbine,
                winddir_cols,
                fov_df,
                elev_fpath,
                direction_array,
                distance_bin_array,
                out_path,
                viewer_height_m,
                obstruction_interval_m,
                max_dist_km,
                save_all,
            )
            futures[future] = turbine

    with tqdm.tqdm(
        total=len(futures),
        desc="Analyzing turbine viewsheds",
        ascii=True,
        file=open(os.devnull, "w"),
    ) as pbar:
        for future in as_completed(futures):
            try:
                future.result()
                pbar.update(1)
                logger.info(pbar)
            except Exception as e:
                raise e.__class__(f"Error with map {futures[future]}: {e}")

    logger.info("Process completed sucessfully.")

    return out_path.as_posix()


def viewshed(
    turbine,
    winddir_cols,
    fov_df,
    elev_fpath,
    direction_array,
    distance_bin_array,
    out_path,
    viewer_height_m,
    obstruction_interval_m,
    max_dist_km,
    save_all,
):
    """
    Runs the turbine-specific/location-specific analysis required for the run()
    function.

    Parameters
    ----------
    turbine : pandas.Series
        Series containing attributes for an individual turbine
    winddir_cols : List[str]
        List of columns containing frequencies/weights for different wind directions.
    fov_df : pandas.DataFrame
        FOV percent lookup dataframe.
    elev_fpath : str
        Path to raster dataset containing elevation values (i.e., DEM or DSM).
        Pixel values should indicate the height of the pixel in meters. Raster must be
        projected to a CRS with linear units of meters.
    direction_array : numpy.ndarray
        Array defining direction of turbine relative to each cell
    distance_bin_array : numpy.ndarray
        Array defining distance bin from turbine for to each cell
    out_path : pathlib.Path
        Output path to which result tifs will be saved
    viewer_height_m : int
        Defines the height of the viewer used in the viewshed analysis, specified in
        units of meters. This should correspond to the camera.height_m used in your
        silouettes config(s).
    obstruction_interval_m : float
        Defines the height interval at which obstructions will be analyzed, specified in
        units of meters. For example, a value of 20 would run viewsheds for a given wind
        turbine starting at the max tip height, at intervals of 20m down to the ground.
        For a turbine with 80m hub height and 80m rotor diameter, this would result in
        viewsheds at the following heights: [120, 100, 80, 60, 40, 20, 0]. This value
        should correspond to the obstruction height intervals used in your fov-lkup CSV.
    max_dist_km : float
        Distance limit for viewshed analysis. Locations farther than this distance away
        from turbines will not be analyzed. Should be specified in units of kilometers.
    save_all : bool, optional
        Flag to control whether to save all intermediate outputs as well as final
        results, by default False.


    Raises
    ------
    ValueError
        A ValueError will be raised if the derived viewshed_array is the wrong shape
        or if any of the winddir_cols specify an angle that is outside the range of
        0 to 360.
    """
    # pylint: disable=too-many-arguments
    turbine_gid = turbine["gid"]

    array_shape = direction_array.shape

    # initialize array to hold the minimum height at which the turbine
    # is visibile for each pixel. initial value is the maximum allowable value
    # for this dtype and should be interpreted as the turbine being not visible
    obst_height_array = np.zeros(array_shape, dtype="uint16")
    obst_height_array[:] = visibility.NOT_VISIBLE_VALUE

    obstruction_heights = visibility.get_obstruction_heights(
        rotor_diameter=turbine["rd_m"],
        hub_height=turbine["hh_m"],
        obstruction_interval=obstruction_interval_m,
    )
    # calculate turbine viewshed for obstruction heights
    for obstruction_height in obstruction_heights:
        viewshed_result = visibility.run_viewshed(
            elevation_src=elev_fpath,
            turbine_x=turbine["geometry"].x,
            turbine_y=turbine["geometry"].y,
            turbine_z=obstruction_height,
            max_distance=max_dist_km * 1000,
            viewer_z=viewer_height_m,
        )
        viewshed_array = viewshed_result.ReadAsArray()
        if viewshed_array.shape != array_shape:
            raise ValueError(
                "Viewshed array does not match expected shape. The input "
                "elevation source may not fully cover the analysis area."
            )

        out_affine = Affine.from_gdal(*viewshed_result.GetGeoTransform())
        out_crs = rasterio.CRS.from_wkt(viewshed_result.GetProjection())

        if save_all:
            raster.save_to_geotiff(
                viewshed_array,
                affine=out_affine,
                crs=out_crs,
                out_tif=out_path.joinpath(
                    f"viewshed_gid{turbine_gid}_ht{obstruction_height}.tif"
                ),
            )

        # convert results so that visible pixels are recoded to the obstruction
        # height, and invisible pixels are coded to the NOT_VISIBLE_VALUE
        visible_height_array = np.where(
            viewshed_array == 1,
            obstruction_height,
            visibility.NOT_VISIBLE_VALUE,
        )
        # combine with prior results to find the minimum height visible over
        # all heights
        obst_height_array = np.minimum(visible_height_array, obst_height_array)

    # derive the look angle and lookup up turbine percent FOV for each pixel and wind
    # direction
    weights = []
    fov_pct_arrays = []
    for winddir_col in winddir_cols:
        # weight applied to this result will be the frequency of time
        # wind is blowing in this direction
        weight = turbine[winddir_col]
        if weight <= 0:
            # skip directions where weight is zero or negative
            continue
        weights.append(weight)

        # turbine bearing is 180 degrees opposite the wind direction
        # use modulo/remainder to keep values 0-360
        winddir = float(winddir_col.split("_", maxsplit=3)[-1])
        if winddir < 0 or winddir > 360:
            raise ValueError("Unexpected wind direction: out of range 0 to 360")
        turbine_bearing = (winddir + 180) % 360

        # derive the lookangle category (FRONT, DIAGONAL, SIDE) for each pixel
        # based on the the direction array and the turbine bearing
        lookangle_array = measures.classify_look_angle(
            direction_from_turbine=direction_array,
            turbine_bearing=turbine_bearing,
        ).astype("int8")

        # get the percent FOV
        fov_pct = visibility.lookup_fov_pct(
            fov_df,
            rotor_diameter_m=turbine["rd_m"],
            hub_height_m=turbine["hh_m"],
            obst_height_array=obst_height_array,
            distance_bin_array=distance_bin_array,
            lookangle_array=lookangle_array,
        )
        fov_pct_arrays.append(fov_pct)

        if save_all:
            raster.save_to_geotiff(
                lookangle_array,
                affine=out_affine,
                crs=out_crs,
                out_tif=out_path.joinpath(
                    f"lookangles_gid{turbine_gid}_bearing" f"{int(turbine_bearing)}.tif"
                ),
            )
            raster.save_to_geotiff(
                fov_pct,
                affine=out_affine,
                crs=out_crs,
                out_tif=out_path.joinpath(
                    f"fov_pct_gid{turbine_gid}_bearing{int(turbine_bearing)}.tif"
                ),
            )

    # stack the fov_pct arrays to a 3D array
    fov_pct_stacked = np.stack(fov_pct_arrays, axis=0)
    # calculated weighted average
    fov_pct_weighted = (
        fov_pct_stacked * np.array(weights)[:, np.newaxis, np.newaxis]
    ).sum(axis=0) / sum(weights)

    # save results
    raster.save_to_geotiff(
        fov_pct_weighted,
        affine=out_affine,
        crs=out_crs,
        out_tif=out_path.joinpath(f"fov-pct_gid{turbine_gid}.tif"),
    )

    if save_all:
        raster.save_to_geotiff(
            direction_array,
            affine=out_affine,
            crs=out_crs,
            out_tif=out_path.joinpath(f"directions_gid{turbine_gid}.tif"),
        )
        raster.save_to_geotiff(
            distance_bin_array.astype("int32"),
            affine=out_affine,
            crs=out_crs,
            out_tif=out_path.joinpath(f"distance-bins_gid{turbine_gid}.tif"),
        )
        raster.save_to_geotiff(
            obst_height_array,
            affine=out_affine,
            crs=out_crs,
            out_tif=out_path.joinpath(f"obst-height_gid{turbine_gid}.tif"),
            nodata_value=visibility.NOT_VISIBLE_VALUE,
        )


viewsheds_cmd = CLICommandFromFunction(
    function=run,
    name="viewsheds",
    add_collect=False,
    config_preprocessor=_preprocessor,
    split_keys=["_skip_features"],
)
main = as_click_command(viewsheds_cmd)


if __name__ == "__main__":
    try:
        main(obj={})
    except Exception:
        LOGGER.exception("Error running via-wind fov CLI.")
        raise
