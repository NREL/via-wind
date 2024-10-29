# -*- coding: utf-8 -*-
"""
mask module - sets up CLI for mask command using nrel-gaps
"""
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

import rasterio
from gaps.cli import as_click_command, CLICommandFromFunction
import numpy as np

from via_wind import __version__
from via_wind.log import init_logger, remove_streamhandlers
from via_wind.utils import verify_file
from via_wind import raster


LOGGER = logging.getLogger(__name__)


def _log_inputs(config):
    """
    Emit log messages summarizing user inputs.

    Parameters
    ----------
    config : dict
        Configuration dictionary
    """
    LOGGER.info(
        "No visibility mask will be applied from the mask raster "
        f"{config['mask_raster']} to the input raster {config['input_raster']}"
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
    log_directory : pathlib.Path
        Path to directory for output log files.
    verbose : bool
        Flag to signal ``DEBUG`` verbosity (``verbose=True``).

    Returns
    -------
    dict
        Configuration dictionary modified to include additional or augmented
        parameters.
    """
    init_logger(job_name, log_directory, module=__name__, verbose=verbose, stream=False)
    verify_file(config["mask_raster"])
    verify_file(config["input_raster"])
    config["_local"] = (
        config.get("execution_control", {}).get("option", "local") == "local"
    )
    _log_inputs(config)

    return config


def run(input_raster, mask_raster, out_dir, _local=True):
    """
    Applies a "no visibility" mask to the input raster. Where values from the
    mask_raster evaluate to True (i.e., are > 0), values from the input raster will be
    set to zero. An example where this may be useful is applying a land cover raster
    set areas with forest cover to zero visibility.

    Parameters
    ----------
    input_raster : str
        Path to input raster to be masked.
    mask_raster : str
        Path to mask raster to be applied. Values > 0 will be treated as "not visible"
        and applied to the input raster. The mask raster must share the same CRS with
        and be coregistered to the input_raster.
    out_dir : str
        Output parent directory. Results will be saved to a subfolder named
        "mask" within this parent directory. If the subfolder does not
        exist, it will be created. If the subfolder does exist, existing files may
        be overwritten. The output saved in the subfolder with a filename matching the
        input raster.
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
        "Starting processing to apply visibility mask to input raster."
    )

    # create folder at the output path
    out_path = Path(out_dir).joinpath("mask").expanduser()
    out_path.mkdir(exist_ok=True, parents=False)

    input_raster_path = Path(input_raster).expanduser()
    mask_raster_path = Path(mask_raster).expanduser()
    out_raster_path = out_path.joinpath(input_raster_path.name)


    LOGGER.info("Checking for matching properties of input and mask rasters")
    in_info = raster.get_raster_info(input_raster_path)
    mask_info = raster.get_raster_info(mask_raster_path)
    for check_key in ["crs", "resolution", "shape"]:
        if in_info.get(check_key) != mask_info.get(check_key):
            raise ValueError(
                f"Input Raster and Mask Raster {check_key} do not match."
            )

    with (
        rasterio.open(input_raster_path, "r") as in_src,
        rasterio.open(mask_raster_path, "r") as mask_src
    ):

        in_transform = in_src.transform
        mask_transform = mask_src.transform
        if not np.isclose(in_transform, mask_transform).all():
            raise ValueError("Input Raster and Mask Raster transform do not match.")

        LOGGER.info("Loading mask")
        vis_mask = mask_src.read(1) <= 0

        LOGGER.info("Applying mask")
        masked = in_src.read(1) * vis_mask

        nodata = in_src.nodata
        tags = in_src.tags()

    LOGGER.info(f"Saving results to {out_raster_path}")
    raster.save_to_geotiff(
        masked,
        affine=in_transform,
        crs=in_info["crs"],
        out_tif=out_raster_path,
        nodata_value=nodata,
        tags=tags
    )

    LOGGER.info("Process completed sucessfully.")

    return out_raster_path.as_posix()


mask_cmd = CLICommandFromFunction(
    function=run,
    name="mask",
    add_collect=False,
    config_preprocessor=_preprocessor,
)
main = as_click_command(mask_cmd)


if __name__ == "__main__":
    try:
        main(obj={})
    except Exception:
        LOGGER.exception("Error running via-wind mask CLI.")
        raise
