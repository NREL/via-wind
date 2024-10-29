# -*- coding: utf-8 -*-
"""
silouettes module - sets up CLI for silouettes command using nrel-gaps
"""
import logging
from pathlib import Path
import shutil
import os

import tqdm
from gaps.cli import as_click_command, CLICommandFromFunction

from via_wind import __version__
from via_wind.log import init_logger, CSilencer
from via_wind.config import SilouettesConfig


LOGGER = logging.getLogger(__name__)


def _parse_silouette_configs(silouette_configs):
    """
    Parses the input silouette configurations to handle the variety of possible inputs
    and return a standardized output. Includes handling for:
    1. List of file paths to configuration files
    2. String defining the path to a single configuration file
    3. String defining the file pattern for multiple configuration files.
    Regardless of the input, the function returns a list of file paths to json files.
    All files in the output are checked to ensure they exist.

    Parameters
    ----------
    silouette_configs : [str, List]
        Input path, paths, or file pattern to silouette configuration JSON files,
        typically from the job config file. Should be one of the following:
        1. List of file paths to configuration files
        2. String defining the path to a single configuration file
        3. String defining the file pattern for multiple configuration files.

    Returns
    -------
    List[str]
        Returns a list of file paths to the silouette configuration files

    Raises
    ------
    FileNotFoundError
        A FileNotFoundError will be raised if any of the inputs paths (or derived paths
        from searching with the input file pattern) do not exist.
    TypeError
        A TypeError will be raised if either the input silouette_configs is an invalid
        type (not str or list) or a single string input to silouettes_config
        is a path to a folder rather than a file.
    """
    if isinstance(silouette_configs, str):
        silouette_configs_path = Path(silouette_configs)
        if "*" in silouette_configs:
            matched_files = [
                f.as_posix()
                for f in silouette_configs_path.parent.glob(silouette_configs_path.name)
            ]
            if len(matched_files) == 0:
                raise FileNotFoundError(
                    "Could not find any files matching the pattern: "
                    f"{silouette_configs}"
                )
            return matched_files

        if silouette_configs_path.exists() is False:
            raise FileNotFoundError(f"Could not find file {silouette_configs_path}")

        if silouette_configs_path.is_file() is False:
            raise TypeError(f"Invalid input {silouette_configs_path}: must be a file")

        return [silouette_configs]

    if isinstance(silouette_configs, list):
        for silouette_config in silouette_configs:
            if Path(silouette_config).exists() is False:
                raise FileNotFoundError(f"Could not find file {silouette_config}")
        return silouette_configs

    raise TypeError("Invalid type for silouettes_config: must be either str or list.")


def _log_inputs(config):
    """
    Emit log messages summarizing user inputs.

    Parameters
    ----------
    config : dict
        Configuration dictionary
    """
    n_configs = len(config["silouette_configs"])
    LOGGER.info(
        f"Silouettes will be simulated in parallel for a total of {n_configs} "
        "configurations (1 per node)"
    )
    LOGGER.info("The following configurations will be simulated: ")
    for silouette_config in config["silouette_configs"]:
        LOGGER.info(f"\t{Path(silouette_config)}")


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
    config["_log_directory"] = log_directory.as_posix()
    config["_verbose"] = verbose
    config["silouette_configs"] = _parse_silouette_configs(config["silouette_configs"])
    config["_local"] = (
        config.get("execution_control", {}).get("option", "local") == "local"
    )
    _log_inputs(config)

    return config


def run(
    silouette_configs,
    out_dir,
    job_name,
    _log_directory,
    _verbose,
    _local=True,
):
    """
    Create silouettes for each of the input configurations, saving all results to
    the specified output directory.

    Parameters
    ----------
    silouette_configs : List[str]
        List of paths to multiple configuration JSON files.
    out_dir : str
        Output parent directory. Results will be saved to a subfolder named
        "silouettes" within this parent directory. If the subfolder does not
        exist, it will be created. If the subfolder does exist, existing files may
        be overwritten.
    job_name : str
        Name of job being run. Derived from the name of the folder containing the
        user configuration file.
    _log_directory : str
        Path to log output directory.
    _verbose : bool
        Flag to signal ``DEBUG`` verbosity (``verbose=True``).
    _local : bool
        Flag indicating whether the code is being run locally or via HPC job
        submissions. NOTE: This is not a user provided parameter - it is determined
        dynamically by based on whether config["execution_control"]["option"] == "local"
        (defaults to True if not specified).
    """
    # create dedicated logger with filehandler for just this subprocess
    logger = init_logger(
        job_name, _log_directory, module=__name__, verbose=_verbose, stream=False
    )

    logger.info(
        f"Starting processing to derive silouette images for {silouette_configs} "
    )

    # create folder at the output path
    out_path = Path(out_dir).joinpath("silouettes").expanduser()
    out_path.mkdir(exist_ok=True, parents=False)

    create_silouettes(silouette_configs, out_path, job_name, _log_directory, _verbose)

    logger.info("Completed processing successfully.")

    return out_path.joinpath("*").as_posix()


def create_silouettes(config, out_path, job_name, _log_directory, _verbose):
    # pylint: disable=import-outside-toplevel
    """
    Simulates turbine silouettes at specified distances and orientations based on the
    turbine, camera, and obstruction configurations specified in the input configuration
    object. Turbine silouettes images are saved as black and white png files in the
    output folder.

    Parameters
    ----------
    config : str
        Path to JSON configuration file.
    out_path : pathlib.Path
        Output parent directory. Results will be saved to a subfolder named based on
        the input config file,  within this parent directory. If the subfolder does not
        exist, it will be created. If the subfolder does exist, existing files may
        be overwritten.
    job_name : str
        Name of the job being run. This is typically a combination of the project
        directory, the command name, and a tag unique to a job.
    _log_directory : str
        Path to log output directory.
    _verbose : bool
        Flag to signal ``DEBUG`` verbosity (``verbose=True``).
    """
    # imports here because bpy has some stdout that you can't turn off and
    # this keeps it from printing unless this function is run
    with CSilencer():
        import bpy
        from via_wind import blender

    # fix paths as needed
    config_path = Path(config).expanduser()

    # create dedicated logger with filehandler for just this subprocess
    log_name = f"{job_name}-{config_path.stem}"
    logger = init_logger(
        log_name, _log_directory, module=__name__, verbose=_verbose, stream=False
    )

    # load config
    logger.info(f"Loading configuration file {config_path}")
    config = SilouettesConfig(config_path)

    # set up new subfolder in output directory based on the config name
    output_path = out_path.joinpath(config.name)
    logger.info(f"Creating output directory {output_path}")
    output_path.mkdir(exist_ok=True, parents=False)

    # copy config to output directory
    logger.info("Copying configuration file to output directory")
    shutil.copy(config_path, output_path.joinpath("config.json"))

    # reset Blender scene
    logger.info("Resetting blender scene")
    with CSilencer():
        bpy.ops.wm.read_factory_settings(use_empty=True)

    # set up scene
    logger.info("Setting up Blender scene and objects")
    scene = blender.configure_scene(config)
    # create world and attach to scene
    world = blender.create_world()
    scene.world = world
    # create sun and add to scene
    sun = blender.create_sun(config)
    scene.collection.objects.link(sun)

    # create surface materials
    turb_mat = blender.create_turbine_surface_material()
    obs_mat = blender.create_obstruction_surface_material()

    # create turbine components
    # Note: these are automatically added to the scene
    rotors = blender.create_rotors(config, surface_material=turb_mat)
    tower = blender.create_tower(config, surface_material=turb_mat)

    # create obstruction
    obstruction = blender.create_obstruction(surface_material=obs_mat)

    # set up camera
    camera = blender.create_camera(config)
    blender.set_camera_tracking(camera, track_to_obj=rotors)
    scene.collection.objects.link(camera)
    scene.camera = camera

    n_iters = (
        len(config.turbine.obstruction_heights)
        * len(config.turbine.distances_to_camera_m)
        * len(config.turbine.rotations)
    )
    with tqdm.tqdm(
        total=n_iters,
        desc="Running Silouette Simulations",
        ascii=True,
        file=open(os.devnull, "w"),
    ) as pbar:
        for obstruction_height in config.turbine.obstruction_heights:
            for distance in config.turbine.distances_to_camera_m:
                for rotation in config.turbine.rotations:
                    # reposition the turbine
                    blender.position_turbine(
                        rotors,
                        tower,
                        config,
                        distance_to_camera_m=distance,
                        rotation=rotation,
                    )

                    # reposition the obstruction
                    blender.position_obstruction(
                        obstruction,
                        config,
                        height_m=obstruction_height,
                        turb_distance_to_camera_m=distance,
                        turb_rotation=rotation,
                    )

                    # render scene to output image
                    out_image = output_path.joinpath(
                        f"d{distance}m-r{rotation}-o{obstruction_height}m.png"
                    )
                    blender.render_image(scene, out_image)

                    # update progress
                    pbar.update(1)
                    logger.info(pbar)

    logger.info(f"Completed silouettes for {config.name}.")


silouettes_cmd = CLICommandFromFunction(
    function=run,
    name="silouettes",
    add_collect=False,
    config_preprocessor=_preprocessor,
    split_keys=["silouette_configs"],
)
main = as_click_command(silouettes_cmd)


if __name__ == "__main__":
    try:
        main(obj={})
    except Exception:
        LOGGER.exception("Error running via-wind silouettes CLI.")
        raise
