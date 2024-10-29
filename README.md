# via-wind: A Visual Impact Assessment Tool for Wind Turbines
**via-wind** is an open-source tool for conducting visual impact assessments for wind turbines.

It combines geographic information system (GIS) and 3D simulation methods to account for the key factors driving the visual impact of installed wind turbines, including distance, viewing angle, turbine orientation, visual exposure, and the cumulative effects of multiple turbines.

This software is optimized for use in high-performance computing environments to enable large scale (e.g., country-wide) analysis, but can also be run on a single server or personal computer.

## Installation
1. Clone the repository
    ```commandline
    git clone git@github.nrel.gov:GDS/via-wind.git
    ```

2. Move into the local repo
    ```command line
    cd via-wind
    ```

3. Recommended: Setup virtual environment with `conda`/`mamba`:
    ```commandline
    mamba env create -f environment.yml
    mamba activate via-wind
    ```
    Note: You may choose an alternative virtual environment solution; however, installation of dependencies is not guaranteed to work.

4. Install `blender` Python module (`bpy`):
    - Option 1: Use builds from blender.org:
        - Download`bpy` build for your OS from https://builder.blender.org/download/bpy/
        - Unzip the wheel from the downloaded zip file
        - Install `bpy` from wheel:
            ```commandline
            pip install <path-to-your-bpy-build.whl>
            # e.g., pip install bpy-3.5.0-cp310-cp310-manylinux_2_28_x86_64.whl
            ```
        - Note: For linux, the wheel file may need to be renamed to work (e.g., replace "manylinux_2_28_" with "linux_"). See: https://stackoverflow.com/a/52661110 for related discussion.
    - Option 2: Build `bpy` module from source
        - See instructions here: https://developer.blender.org/docs/handbook/building_blender/python_module/#building-blender-as-a-python-module

5. Install `via_wind` package:
    - For users: `pip install .`
    - For developers: `pip install -e '.[dev]'`

6. **Developers Only** Install pre-commit
    ```commandline
    pre-commit install
    ```

## Usage
Refer to the [Usage](USAGE.md) documentation.

## Developers
Some unit tests may fail due to checks of content of output files, which may differ slightly across operating systems. To skip these issues, you can run `pytest --skip_content_check`.

## Additional Information
NREL Software Record number SWR-24-87.