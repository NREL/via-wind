"""via-wind"""
from pathlib import Path

from via_wind.version import __version__

__author__ = "Michael Gleason"
__email__ = "mike.gleason@nrel.gov"

PACKAGE_DIR = Path(__file__).parent
CONFIGS_DIR = PACKAGE_DIR.joinpath("configs")
DATA_DIR = PACKAGE_DIR.joinpath("data")

CALIBRATION_MODEL = DATA_DIR.joinpath(
    "models", "ordered_probit_vis_impact_cat_by_log_fov_pct_20240307T0947.pkl"
)
