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

4. Install `via_wind` package:
    - For users: `pip install .`
    - For developers: `pip install -e '.[dev]'`

5. **Developers Only** Install pre-commit
    ```commandline
    pre-commit install
    ```

## Usage
Refer to the [Usage](USAGE.md) documentation.

## Developers
Some unit tests may fail due to checks of content of output files, which may differ slightly across operating systems. To skip these issues, you can run `pytest --skip_content_check`.

## Additional Information
NREL Software Record number SWR-24-87.