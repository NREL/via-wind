# -*- coding: utf-8 -*-
"""
merge module - sets up CLI for merge command using nrel-gaps
"""
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from itertools import product

import tqdm
from gaps.cli import as_click_command, CLICommandFromFunction
import numpy as np

from via_wind import __version__
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
        "Viewshed rasters will be merged from the input directory "
        f"{config['viewsheds_directory']}"
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
    config.setdefault("block_size", 3600)
    verify_directory(config["viewsheds_directory"])
    config["_local"] = (
        config.get("execution_control", {}).get("option", "local") == "local"
    )
    _log_inputs(config)

    return config


def run(viewsheds_directory, out_dir, block_size=3600, max_workers=None, _local=True):
    """
    Merges the results from the viewsheds command to create a single raster that sums
    the total percent FOV occupied by all turbines at each location. Should be used
    for cumulative visual impact analysis from one or more wind farms.

    Parameters
    ----------
    viewsheds_directory : str
        Path to directory containing viewshed rasters created by viewsheds command.
    out_dir : str
        Output parent directory. Results will be saved to a subfolder named
        "viewsheds_merge" within this parent directory. If the subfolder does not
        exist, it will be created. If the subfolder does exist, existing files may
        be overwritten.
    block_size : int, optional
        Size of blocks used for mosaicking overlapping viewshed tifs, by default 3600.
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

    LOGGER.info("Starting processing to merge and sum viewshed rasters.")

    # create folder at the output path
    out_path = Path(out_dir).joinpath("viewsheds_merge").expanduser()
    out_path.mkdir(exist_ok=True, parents=False)

    viewsheds_path = Path(viewsheds_directory).expanduser()

    LOGGER.info("Creating VRT")
    vrt_path = out_path.joinpath("sources.vrt")
    raster.create_vrt(viewsheds_path, vrt_path, pattern="fov-pct*.tif")

    LOGGER.info("Getting metadata from VRT")
    vrt_info = raster.get_raster_info(vrt_path)
    vrt_height, vrt_width = vrt_info["shape"]
    vrt_profile = vrt_info["profile"].copy()

    LOGGER.info("Constructing index of source GeoTiff boundaries")
    vrt_sources_df = raster.read_vrt_sources(vrt_path)

    LOGGER.info("Mosaicking blocks")
    blocks_path = out_path.joinpath("blocks")
    blocks_path.mkdir(exist_ok=True)
    row_offsets = np.arange(0, vrt_height + 1, block_size)
    col_offsets = np.arange(0, vrt_width + 1, block_size)
    offsets = list(product(row_offsets, col_offsets))

    futures = {}
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        for row_offset, col_offset in offsets:
            future = pool.submit(
                raster.mosaic_block,
                vrt_sources_df,
                vrt_profile,
                blocks_path,
                col_offset,
                row_offset,
                block_size,
            )
            futures[future] = (row_offset, col_offset)

    with tqdm.tqdm(
        total=len(futures),
        desc="Mosaicking blocks",
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
    raster.merge_tifs(
        blocks_path, out_path.joinpath("fov-pct_sum.tif"), pattern="block*.tif"
    )

    LOGGER.info("Process completed sucessfully.")

    return out_path.as_posix()


merge_cmd = CLICommandFromFunction(
    function=run,
    name="merge",
    add_collect=False,
    config_preprocessor=_preprocessor,
)
main = as_click_command(merge_cmd)


if __name__ == "__main__":
    try:
        main(obj={})
    except Exception:
        LOGGER.exception("Error running via-wind merge CLI.")
        raise
