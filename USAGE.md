# Usage Instructions
## Command Line Interface
This library includes a Command Line Interface (CLI) named `via` that can be used to run a complete pipeline of visual impact analysis for dataset of turbine locations.

### Overview of Commands
There are six commands in the `via` CLI, which are intended to be run in order, as described below:
1. `silouettes`: Creates silouettes of simplified 3D models of turbine at various distances, orientations, and levels of obstruction from the viewer. Configuration of the turbine dimensions and other parameters is provided by the user, and can be performed for multiple configuration files at a time.
2. `fov`: Analyzes the output images from the `silouettes` command to determine the percent of a viewer's field-of-view  (FOV)that is occupied by the turbine model in each of the output images. The output is a CSV  that contains a lookup table for determining the FOV of a turbine based on its dimensions, distance from the viewer, orientation from the viewer, and how much of the turbine is visible based on other visual screening or obstructions.
3. `viewsheds`: Given an input turbine vector GIS dataset, a Digital Surface Model (DSM) raster GIS dataset, and a small number of other user-input parameters, produces a raster for each turbine identifying the percent FOV that the turbine occupies for a hypothetical viewer in each cell of the surrounding area.
4. `merge`: Merges and sums the output rasters from the `viewsheds` command, to summarize the cumulative percent FOV occupied by all turbines at each location analyzed. The output is a seamless raster covering the area around the input turbines.
5. `calibrate`: Calibrates the cumulative FOV percent raster from `merge` and converts values to a scale of visual impact, ranging from `0` (No Turbines Visible) to `4` (High Visual Impact)
6. `mask`: This command can be run optionally to apply a "no visibility" mask to one or both of the outputs from the `merge` command or the `calbrate` command. This is useful in cases where you used a DSM for the `viewsheds` command and want to force set the visibility percent or rating to zero in areas such as forests, where the results will be based on a top-of-canopy view rather than the view below th canopy from the forest floor.

### Running Commands
The `via` CLI is built upon the `gaps` package, which is a framework intended to enable scaling of geospatial python models to leverage High Performance Computing (HPC) systems.

For more background on `gaps`, users are referred to the following links:
- https://nrel.github.io/gaps/index.html
- https://github.com/NREL/gaps

To leverage the capability of `gaps`, the `via` CLI requires that each command be kicked off with a configuration JSON file. The syntax for running a command is typically `via <command> -c config.json`.

Users can find example configuration files for runs on an HPC environment [here](examples/job_configs/hpc/) and for runs on a local environment [here](examples/job_configs/local). Users can also generate template-configs for all commands by running `via template-configs`. Lastly, more information about the configuration parameters for each command can be found by running `via <command> --help`.

For a deeper dive into the capabilities of `gaps` and other utility commands that are available through `via`, users should see: https://nrel.github.io/gaps/misc/examples.users.html.

### Pipelines
One of the advantages of `gaps` is that it is possible to run all the commands together as a single pipeline, by creating an additional "pipeline" configuration file (e.g., `config_pipeline.json`) and then using the command `via pipeline -c config_pipeline. json`. Users are referred to the links in the preceding paragraph for example pipeline configuration files.

### Data Requirements
To run the complete pipeline, users must have or create four main pieces of data:
1. A GIS vector dataset of turbine locations and key characteristics\
This should be a point dataset in GIS vector format (e.g., GeoPackage, Shapefile), and must have the following attributes:
    - `gid`: Unique integer identifying each turbine
    - `rd_m`: Rotor diameter of the turbine, in meters
    - `hh_m`: Hub height of the turbine, in meters
    - `geometry`: Point geometry of the turbine location
    - `freq_winddir_###`: One or more columns indicating the frequency of time that the wind blows in a given direction at the turbine location. For example, for frequencies only consiering the four cardinal directions, four columns would be expected: `freq_winddir_0` (N), `freq_winddir_90` (E), `freq_winddir_180` (S), and `freq_winddir_270` (W). Ideally, this will include 8 directions, accounting for wind directions 45 (NE), 135 (SE), 215 (SW), and 315 (NW) in addition to the cardinal directions.
2. A GIS raster dataset of a Digital Surface Model (DSM)\
This dataset must be projected to a linear unit of meters and should cover the extent of the turbines and the area around the turbines to be analyzed.
3. A "Silouette" configuration file for every combination of rotor diameter and hub height included in the turbines dataset\
Example silouette configuration files can be found [here](examples/silouette_configs). In general, users should only change the "name" and "turbine" sections of the config. Obstruction heights should span the full range from 0 to the maximum tip height of the given turbine and distances_to_camera_m should span from close to the turbine (e.g., 150 meters) to the outer range of distnace at which visibility will be analyzed (e.g., 80 km).
4. Additional parameters controlling the `viewsheds` analysis, all derived from the silouette configurations: `obstruction_interval_m`, `max_dist_km`, and `viewer_height_m`.
