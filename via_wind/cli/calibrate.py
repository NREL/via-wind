# -*- coding: utf-8 -*-
"""
calibrate module - sets up CLI for calibrate command using nrel-gaps
"""
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

import statsmodels.api as sm
import rasterio
import tqdm
from gaps.cli import as_click_command, CLICommandFromFunction
import numpy as np

from via_wind import __version__, CALIBRATION_MODEL
from via_wind.log import init_logger, remove_streamhandlers
from via_wind.utils import verify_directory
from via_wind import raster


LOGGER = logging.getLogger(__name__)


def _log_inputs(config):
    """
    Emit log messages summarizing user inputs

    Parameters
    ----------
    config : dict
        Configuration dictionary
    """
    LOGGER.info(
        "Calibrated visual impact rasters will be derived from the input directory "
        f"{config['merge_directory']}"
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
    verify_directory(config["merge_directory"])
    config["_local"] = (
        config.get("execution_control", {}).get("option", "local") == "local"
    )
    _log_inputs(config)

    return config


def run(merge_directory, out_dir, max_workers=None, _local=True):
    """
    Calibrates the results from merge command to create a single raster that provides
    a visual impact score for each pixel. Should be used for cumulative visual impact
    analysis from one or more wind farms. Output values should be interpreted as
    follows:
        0: No Turbines Visible
        1: Minimal Visual Impact
        2: Low Visual Impact
        3: Moderate Visual Impact
        4: High Visual Impact

    Parameters
    ----------
    merge_directory : str
        Path to directory of merged viewshed rasters created by merge command.
    out_dir : str
        Output folder to which simulated turbine silouettes will be saved. If the folder
        does not exist, it will be created. If the folder does exist, existing files may
        be overwritten.
    max_workers : [int, NoneType], optional
        Maximum number of workers to use for multiprocessing, by default None, which
        uses all available CPUs.
    _local : bool
        Flag indicating whether the code is being run locally or via HPC job
        submissions. NOTE: This is not a user provided parameter - it is determined
        dynamically by based on whether config["execution_control"]["option"] == "local"
        (defaults to True if not specified).
    """
    # streamhandler is added in by gaps before kicking off the subprocess and
    # will produce duplicate log messages if running locally, so remove it
    if _local:
        remove_streamhandlers(LOGGER.parent)

    LOGGER.info(
        "Starting processing to calbirate FOV percent values to visual impact scores."
    )

    # create folder at the output path
    out_path = Path(out_dir).joinpath("viewsheds_calibrated").expanduser()
    out_path.mkdir(exist_ok=True, parents=False)

    merge_path = Path(merge_directory).expanduser()

    LOGGER.info("Loading calibration model")
    model = sm.load(CALIBRATION_MODEL)

    pixel_value_descriptions = {
        "0": "No Turbines Visible",
        "1": "Minimal Visual Impact",
        "2": "Low Visual Impact",
        "3": "Moderate Visual Impact",
        "4": "High Visual Impact",
        "5": "Very High Visual Impact",
    }

    out_blocks_path = out_path.joinpath("blocks")
    out_blocks_path.mkdir(exist_ok=True)
    in_blocks_path = merge_path.joinpath("blocks")
    in_block_tifs = list(in_blocks_path.glob("*.tif"))
    LOGGER.info("Calibrating blocks")

    futures = {}
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        for in_block_tif in in_block_tifs:
            future = pool.submit(
                calibrate,
                in_block_tif,
                model,
                out_blocks_path,
                pixel_value_descriptions,
            )
            futures[future] = in_block_tif

    with tqdm.tqdm(
        total=len(futures),
        desc="Calbirating blocks",
        ascii=True,
        file=open(os.devnull, "w"),
    ) as pbar:
        for future in as_completed(futures):
            try:
                future.result()
                pbar.update(1)
                LOGGER.info(pbar)
            except Exception as e:
                raise e.__class__(f"Error with map {futures[future]}: {e}")

    LOGGER.info("Merging blocks")
    out_merged_tif = out_path.joinpath("visual_impact.tif")
    raster.merge_tifs(out_blocks_path, out_merged_tif, pattern="block*.tif")
    # add descriptions of pixel values as metadata
    with rasterio.open(out_merged_tif, "r+") as rast:
        rast.update_tags(**pixel_value_descriptions)

    LOGGER.info("Process completed sucessfully.")

    return out_merged_tif.as_posix()


def calibrate(viewshed_tif, stats_model, out_path, pixel_value_descriptions):
    """
    Calibrate an individual viewshed geotiff to visual impact ratings using the
    specified stats model.

    Parameters
    ----------
    viewshed_tif : str
        Path to merged viewshed tif (can be either a block or the full mosaicked tif)
    stats_model : statsmodels.miscmodels.ordinal_model.OrderedResultsWrapper
        Statistical (Ordinal Regression) model used for calibration of the values in the
        merged viewshed tif to calibrated visual impact ratings.
    out_path : str
        Path to output directory where the calibrated tif will be saved. Output tif
        will have the same name as the viewshed_tif.
    pixel_value_descriptions : dict
        Dictionary describing the meaning of the output rating values.
    """
    with rasterio.open(viewshed_tif, "r") as rast:
        fov_pct = rast.read(1)
        crs = rast.crs
        profile = rast.profile

    # log transform the input fov_pct values and reshape for input to the model
    # note: fov_pct = 0 -> Turbines not visible, and is out of range for np.log,
    # so mask these pixels out for now
    nonzero = fov_pct > 0
    x_data = np.log(fov_pct[nonzero]).ravel().reshape(-1, 1)

    # make predictions
    predicted = stats_model.model.predict(stats_model.params, exog=x_data, which="prob")
    pred_choice = predicted.argmax(1)
    # create the result raster
    # note: 0 = not visible, so all other values have to be increased by 1
    calibrated = np.zeros(fov_pct.shape, dtype="int8")
    calibrated[nonzero] = pred_choice + 1

    # calibration model wasn't trained on data with fov_pct = 0 (i.e., turbines not
    # visible), so manually override these values and set to 0
    calibrated[fov_pct == 0] = 0

    out_tif = out_path.joinpath(viewshed_tif.name)
    raster.save_to_geotiff(
        calibrated,
        affine=profile["transform"],
        crs=crs,
        out_tif=out_tif,
        nodata_value=None,
        tags=pixel_value_descriptions,
    )


calibrate_cmd = CLICommandFromFunction(
    function=run,
    name="calibrate",
    add_collect=False,
    config_preprocessor=_preprocessor,
)
main = as_click_command(calibrate_cmd)


if __name__ == "__main__":
    try:
        main(obj={})
    except Exception:
        LOGGER.exception("Error running via-wind fov CLI.")
        raise
