# -*- coding: utf-8 -*-
"""via-wind GAPS command line interface"""
import logging

from gaps.cli.cli import make_cli

from via_wind import __version__
from via_wind.cli.silouettes import silouettes_cmd
from via_wind.cli.fov import fov_cmd
from via_wind.cli.viewshed import viewsheds_cmd
from via_wind.cli.merge import merge_cmd
from via_wind.cli.calibrate import calibrate_cmd
from via_wind.cli.mask import mask_cmd


logger = logging.getLogger(__name__)

commands = [silouettes_cmd, fov_cmd, viewsheds_cmd, merge_cmd, calibrate_cmd, mask_cmd]
main = make_cli(commands, info={"name": "via-wind", "version": __version__})

if __name__ == "__main__":
    try:
        main(obj={})
    except Exception:
        logger.exception("Error running via-wind CLI")
        raise
