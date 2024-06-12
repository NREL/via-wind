# via-wind
Perform visual impact assessment for wind turbines using a combination of 3D simulation of turbines of varying dimensions and orientations, and GIS analysis.

## Installation
1. Clone the repo
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

4. Download blender compiled as Python module
- Download zip for your OS from https://builder.blender.org/download/bpy/
- Unzip the wheel from the zip file

5. Install blender python module
```commandline
pip install <path-to-your-bpy-build.whl>
# e.g., pip install bpy-3.5.0-cp310-cp310-manylinux_2_28_x86_64.whl
```
Note: For linux, the wheel file may need to be renamed to work (e.g., replace "manylinux_2_28_" with "linux_"). See: https://stackoverflow.com/a/52661110 for explanation.

6. Install `via_wind` package:
    - For users: `pip install .`
    - For developers: `pip install -e '.[dev]'`

7. **Developers Only** Install pre-commit
```commandline
pre-commit install
```

## Usage
Refer to the [Usage](USAGE.md) documentation.

## Developers
Some unit test may fail due to checks of content of output files, which may different slightly from actual outputs when the software is run on a different operating system. To skip these issues, you can run `pytest --skip_content_check`.
