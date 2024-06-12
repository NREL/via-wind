# -*- coding: utf-8 -*-
"""
For loading/handling configuration files
"""
from numbers import Number
import json
from dataclasses import dataclass
from typing import List, _GenericAlias


@dataclass
class BaseParams:
    # pylint: disable=no-member
    """
    Base dataclass to be used for loading parameters from a dictionary.
    """

    def __init__(self, params_dict):
        """
        Initialize the dataclass, loading all known data attributes from the input
        dictionary.

        Parameters
        ----------
        params_dict : dict
            Input dictionary. Should contain all required attributes of the data
            class.

        Raises
        ------
        ValueError
            A ValueError will be raised if a required attribute is not found in the
            input dictionary.
        TypeError
            A TypeError will be raised if a required attribute is found in the input
            dictionary but is not the correct datatype.
        """
        if not isinstance(params_dict, dict):
            raise TypeError(
                f"Invalid input for {self.__class__}: must be a dictionary/mapping."
            )

        for attr, dtype in self.__annotations__.items():
            # special handling for List[*] dtypes: set dtype to List and get dtype for
            # list elements
            if isinstance(dtype, _GenericAlias) and dtype._name == "List":
                elements_dtype = dtype.__args__
                dtype = list
            else:
                elements_dtype = None

            value = params_dict.get(attr)

            if value is None:
                raise ValueError(f"{attr} is missing from input.")

            if not isinstance(value, dtype):
                raise TypeError(f"Invalid input for {attr}: must be type {dtype}")

            if elements_dtype is not None:
                # check the dtype of the elements of the list
                for v in value:
                    if not isinstance(v, elements_dtype):
                        raise TypeError(
                            f"Invalid input for {attr}:"
                            f" elements must be type {elements_dtype}"
                        )

            setattr(self, attr, value)


class TurbineParams(BaseParams):
    # pylint: disable=too-few-public-methods
    """Dataclass defining Turbine parameters for silouettes simulation."""

    blade_chord_m: Number
    distances_to_camera_m: List[Number]
    hub_height_m: Number
    obstruction_heights: List[Number]
    rotations: List[str]
    rotor_diameter_m: Number
    rotor_overhang_m: Number
    tower_diameter_m: Number


class CameraParams(BaseParams):
    # pylint: disable=too-few-public-methods
    """Dataclass defining Camera parameters for silouettes simulation."""

    film_width_mm: Number
    height_m: Number
    lens_mm: Number
    output_resolution_height: Number
    output_resolution_width: Number


@dataclass
class SilouettesConfig:
    # pylint: disable=no-member
    """
    Configuration class for storing input configuration parameters for silouettes
    simulation.
    """

    name: str
    turbine: TurbineParams
    camera: CameraParams

    def __init__(self, config_path):
        """
        Load configuration from JSON file.

        Parameters
        ----------
        config_path : [str, pathlib.Path]
            Path to configuration JSON file.

        Returns
        -------
        Config
            Dataclass storing configuration parameters for silouettes simulation
        """

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        for attr, dtype in self.__annotations__.items():
            value = config_data.get(attr)

            if value is None:
                raise ValueError(f"{attr} is missing from input.")

            try:
                setattr(self, attr, dtype(value))
            except (ValueError, TypeError) as e:
                raise TypeError(
                    f"Invalid input for {attr}: must be type {dtype}"
                ) from e
