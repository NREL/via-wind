# -*- coding: utf-8 -*-
"""
fov module - sets up CLI for fov command using nrel-gaps
"""
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

import tqdm
from gaps.cli import as_click_command, CLICommandFromFunction
import numpy as np
import pandas as pd

from via_wind import __version__
from via_wind.log import init_logger, remove_streamhandlers
from via_wind.config import SilouettesConfig
from via_wind.image import mean_image_intensity


LOGGER = logging.getLogger(__name__)


def _parse_silouette_directories(silouette_directories):
    """
    Parses the input silouette directories to handle the variety of possible inputs
    and return a standardized output. Includes handling for:
    1. List of paths to silouette folders
    2. String defining the path to a single silouette folder
    3. String defining the path to a parent directory containing multiple silouette
    subfolders. Must end with "/*" to indicate this should be treated as a parent
    directory.
    Regardless of the input, the function returns a list of paths to silouette folders.
    All folders in the output are checked to ensure they exist.

    Parameters
    ----------
    silouette_directories : [str, List]
        Input path, paths, or file pattern to silouette directories,
        typically from the job config file. Should be one of the following:
        1. List of paths to silouette folders
        2. String defining the path to a single silouette folder
        3. String defining the path to a parent directory containing multiple silouette
        subfolders. Must end with "/*" to indicate this should be treated as a parent
        directory.

    Returns
    -------
    List[str]
        Returns a list of paths to silouette folders

    Raises
    ------
    FileNotFoundError
        A FileNotFoundError will be raised if any of the inputs paths (or derived paths
        from searching with the input file pattern) do not exist.
    TypeError
        A TypeError will be raised if either the input silouette_directories is an
        invalid type (not str or list) or a single string input to silouette_directories
        is a path to a file rather than a folder.
    """
    if isinstance(silouette_directories, str):
        silouette_directories_path = Path(silouette_directories)
        if silouette_directories.endswith("*"):
            matched_folders = [
                d.as_posix()
                for d in silouette_directories_path.parent.glob("*")
                if d.is_dir()
            ]
            if len(matched_folders) == 0:
                raise FileNotFoundError(
                    "Could not find any subdirectories within  "
                    f"{silouette_directories_path.parent}"
                )
            return matched_folders

        if silouette_directories_path.exists() is False:
            raise FileNotFoundError(
                f"Could not find folder {silouette_directories_path}"
            )

        if silouette_directories_path.is_dir() is False:
            raise TypeError(
                f"Invalid input {silouette_directories_path}: must be a folder"
            )

        return [silouette_directories]

    if isinstance(silouette_directories, list):
        for silouette_directory in silouette_directories:
            if Path(silouette_directory).exists() is False:
                raise FileNotFoundError(f"Could not find folder {silouette_directory}")
        return silouette_directories

    raise TypeError(
        "Invalid type for silouette_directories: must be either str or list."
    )


def _log_inputs(config):
    """
    Emit log messages summarizing user inputs

    Parameters
    ----------
    config : dict
        Configuration dictionary
    """
    n_directories = len(config["silouette_directories"])
    LOGGER.info(
        f"Field-of-View will be analyzed for a total of {n_directories} silouette "
        "folders"
    )
    LOGGER.info("The following folders will be analyzed: ")
    for silouette_directory in config["silouette_directories"]:
        LOGGER.info(f"\t{Path(silouette_directory)}")


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
    # load silouette configurations from source directory
    # TODO: split up basewd on # nodes in cofig then create list of lists
    config["silouette_directories"] = _parse_silouette_directories(
        config["silouette_directories"]
    )
    config["_local"] = (
        config.get("execution_control", {}).get("option", "local") == "local"
    )
    _log_inputs(config)

    return config


def run(
    silouette_directories,
    out_dir,
    _log_directory,
    _verbose,
    max_workers=None,
    _local=True,
):
    """
    Analyze field-of-view for all images in each of the input silouette directories,
    saving the result for each to a separate CSV in the specified output directory.

    Parameters
    ----------
    silouette_directories : List[str]

    out_dir : str
        Output folder to which simulated turbine silouettes will be saved. If the folder
        does not exist, it will be created. If the folder does exist, existing files may
        be overwritten.
    _log_directory : str
        Path to log output directory.
    _verbose : bool
        Flag to signal ``DEBUG`` verbosity (``verbose=True``).
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

    LOGGER.info("Starting processing to analyze FOV for silouettes")

    # create folder at the output path
    out_path = Path(out_dir).joinpath("fov").expanduser()
    out_path.mkdir(exist_ok=True, parents=False)

    futures = {}
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        for silouette_directory in silouette_directories:
            future = pool.submit(
                calc_fov, silouette_directory, out_path, _log_directory, _verbose
            )
            futures[future] = silouette_directory

    fov_dfs = []
    for future in as_completed(futures):
        try:
            out_csv = future.result()
        except Exception as e:
            raise e.__class__(f"Error with map {futures[future]}: {e}")

        fov_dfs.append(pd.read_csv(out_csv))

    LOGGER.info("Successfully completed analyzing FOV for all directories.")

    LOGGER.info("Merging results")
    all_fov_df = pd.concat(fov_dfs, ignore_index=True)

    out_all_csv = Path(out_path).joinpath("combined_fov_lkup.csv")
    LOGGER.info(f"Saving combined FOV lookup CSV to {out_all_csv}")
    all_fov_df.to_csv(out_all_csv, header=True, index=False)

    LOGGER.info("All processing completed successfully.")

    return out_all_csv.as_posix()


def calc_fov(silouette_directory, out_path, log_directory, verbose):
    """
    Analyze silouette images to determine the percent of the field-of-view (FOV)
    occupied by each configuration of the turbine. Results from all images are compiled
    and saved to a CSV with the percent FOV values and key parameters of the turbine
    configuration (e.g., distance, rotation, obstruction height, etc.).

    Parameters
    ----------
    silouette_directory : str
        Path to directory containing silouette images output by ``silouettes`` command.
    out_path : pathlib.Path
        Output folder to which simulated turbine silouettes will be saved. If the folder
        does not exist, it will be created. If the folder does exist, existing files may
        be overwritten.
    log_directory : str
        Path to log output directory.
    verbose : bool
        Flag to signal ``DEBUG`` verbosity (``verbose=True``).
    """

    img_path = Path(silouette_directory)

    # create dedicated logger with filehandler for just this subprocess
    log_name = f"calc_fov_{img_path.stem}"
    logger = init_logger(
        log_name, log_directory, module="via_wind", verbose=verbose, stream=False
    )

    logger.info("Finding silouette images to analyze")
    images = list(img_path.glob("*.png"))

    # read in turbine configuration parameters
    try:
        config = SilouettesConfig(img_path.joinpath("config.json"))
        turbine_params = config.turbine.__dict__.copy()
        turbine_params.pop("distances_to_camera_m")
        turbine_params.pop("obstruction_heights")
        turbine_params.pop("rotations")
    except FileNotFoundError:
        logger.warning(
            f"Configuration file could not be found in {silouette_directory}. "
            "Some turbine parameters will not be included in output CSV."
        )

    # determine how much of a full field-of-view is occupied by a single image:
    # assumes that the full FOV is fixed in the vertical direction (i.e., viewer does
    # not look up or down) but can rotate a full 360 degrees in the horizontal
    # direction) based on an assumption of staring out at the horizon
    film_height_mm = 24  # default setting in blender
    film_width_mm = config.camera.film_width_mm
    lens_mm = config.camera.lens_mm

    # this is a well-established formula for deriving the angular FOV for a camera
    photo_fov_vertical = np.rad2deg(2 * np.arctan(film_height_mm / (lens_mm * 2)))
    photo_fov_horizontal = np.rad2deg(2 * np.arctan(film_width_mm / (lens_mm * 2)))

    # From Minelli et al. 2014
    # https://www.sciencedirect.com/science/article/pii/S0195925514000675
    full_fov_vertical = 135
    full_fov_horizontal = 360

    photo_to_full_fov_ratio = (
        photo_fov_vertical
        / full_fov_vertical
        * photo_fov_horizontal
        / full_fov_horizontal
    )

    results = []
    with tqdm.tqdm(
        total=len(images),
        desc="Analyzing silouettes",
        ascii=True,
        file=open(os.devnull, "w"),
    ) as pbar:
        for image in images:
            # calculate the visual impact of the turbine
            # (i.e., the % of the FOV occupied by the turbine silouette)
            vis_impact = mean_image_intensity(image) * photo_to_full_fov_ratio

            # parse the image name to determine the distance of the turbine from the
            # camera, the rotation of the turbine, and the obstruction height
            dist, rot, obs = image.name.replace(".png", "").split("-", maxsplit=3)

            image_data = turbine_params.copy()
            image_data.update(
                {
                    "distance_m": float(dist.replace("d", "").replace("m", "")),
                    "rotation": rot.replace("r", ""),
                    "obstruction_height_m": float(
                        obs.replace("o", "").replace("m", "")
                    ),
                    "pct_fov": round(vis_impact * 100, 5),
                }
            )
            results.append(image_data)
            pbar.update(1)
            logger.info(pbar)

    logger.info("Combining and saving results.")
    results_df = pd.DataFrame(results)
    results_df.sort_values(
        by=["rotation", "distance_m", "obstruction_height_m"],
        ascending=True,
        inplace=True,
    )

    out_csv = out_path.joinpath(f"{img_path.name}.csv")
    results_df.to_csv(out_csv, header=True, index=False)
    logger.info("Process completed successfully.")

    return out_csv


fov_cmd = CLICommandFromFunction(
    function=run,
    name="fov",
    add_collect=False,
    config_preprocessor=_preprocessor,
)
main = as_click_command(fov_cmd)


if __name__ == "__main__":
    try:
        main(obj={})
    except Exception:
        LOGGER.exception("Error running via-wind fov CLI.")
        raise
