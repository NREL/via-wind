# -*- coding: utf-8 -*-
"""
Implements basic mechanics of setting up blender scene, camera, lighting, simplified
turbine model, and obstruction. Exports resulting view from camera to an image.
"""
from pathlib import Path
import warnings
import math

import bpy
import numpy as np
from via_wind.log import CSilencer


# CONSTANTS
# Note: camera clip start and minimum distance affect whether parts of the scene
# will be trimmed at short distances. These settings seem suitable for typical turbine
# dimensions
CAMERA_CLIP_START = 100
MINIMUM_DISTANCE = 150
N_CYLINDER_VERTICES = 100
OBSTRUCTION_WIDTH_M = 500.0
OBSTRUCTION_DEPTH_M = 2
OBSTRUCTION_ROTATION = (0, 90, 0)
BLACK_RGB = (0, 0, 0)
BLACK_RGBA = (0, 0, 0, 1)
WHITE_RGB = (1, 1, 1)
WHITE_RGBA = (1, 1, 1, 1)
RED_RGBA = (1, 0, 0, 1)
VALID_ROTATIONS = {"FRONT": (0, 90, 0), "SIDE": (90, 90, 0), "DIAGONAL": (45, 90, 0)}


def configure_scene(config):
    """
    Create and configure the Blender "scene", including setting the output image
    resolution, color mode, and view transform.

    Parameters
    ----------
    config : via_wind.config.Config
        Configuration namespace. Must contain "camera" property with subproperties
        "output_resolution_width" and "output_resolution_height".

    Returns
    -------
    bpy.types.Scene
        Returns Blender scene
    """
    scene = bpy.context.scene
    # this sets the background so that it will be opaque
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = config.camera.output_resolution_width
    scene.render.resolution_y = config.camera.output_resolution_height
    # output to black and white image
    scene.render.image_settings.color_mode = "BW"

    return scene


def create_world():
    """
    Create and configure the Blender "world", including setting background color to
    white and disabling mist.

    Returns
    -------
    bpy.types.World
        Returns Blender world.
    """
    # set up the world
    world = bpy.data.worlds.new("World")
    # set to white
    world.color = WHITE_RGB
    # disable mist
    world.mist_settings.use_mist = False

    return world


def create_sun(config):
    """
    Create and configure the Blender "sun", including setting its color, location,
     angle, strength, and disabling shadows.

    Parameters
    ----------
    config : via_wind.config.Config
        Configuration namespace. Must contain "camera" property with subproperty
        "height_m".

    Returns
    -------
    bpy_types.Object
        Returns sun as a Blender Object with type "light"
    """

    # define sun settings
    sun_data = bpy.data.lights.new("Sun", type="SUN")
    # make it white
    sun_data.color = WHITE_RGB
    sun_data.angle = 0
    # no shadows
    sun_data.use_shadow = False
    # set strength
    sun_data.energy = 1

    # create and position the sun (same position as the camera)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (0, 0, config.camera.height_m)

    return sun


def create_turbine_surface_material(color=BLACK_RGBA):
    """
    Create the surface material typically used for rendering of turbine tower and rotor
    area. Material is matte (no reflection) and the specified color.

    Parameters
    ----------
    color : tuple, optional
        Four element tuple specifying Red, Green, Blue, and Alpha (RGBA) color to be
        used for the material. By default, this is black and fully opaque.

    Returns
    -------
    bpy.types.Material
        Returns Blender Material to be used for turbine rendering.
    """
    turb_mat = bpy.data.materials.new(name="TurbineMaterial")
    turb_mat.specular_intensity = 0
    turb_mat.roughness = 0
    turb_mat.metallic = 0
    turb_mat.diffuse_color = color

    return turb_mat


def create_obstruction_surface_material(color=WHITE_RGBA):
    """
    Create the surface material typically used for rendering of the obstruction that
    is placed in front of the turbine. Material is matte (no reflection) and the
    specified color.

    Parameters
    ----------
    color : tuple, optional
        Four element tuple specifying Red, Green, Blue, and Alpha (RGBA) color to be
        used for the material. By default, this is white and fully opaque.

    Returns
    -------
    bpy.types.Material
        Returns Blender Material to be used for obstruction rendering.
    """
    obs_mat = bpy.data.materials.new(name="ObstructionMaterial")
    obs_mat.specular_intensity = 0
    obs_mat.roughness = 0
    obs_mat.metallic = 0
    obs_mat.diffuse_color = color

    return obs_mat


def create_rotors(
    config,
    surface_material,
    distance_from_camera_m=0,
    rotation=VALID_ROTATIONS["FRONT"],
    n_vertices=N_CYLINDER_VERTICES,
):
    """
    Create and configure the turbine "rotors" to be used in the silouettes. The rotors
    are created as a flattened cylinder with the round ends oriented perpendicular
    to the ground. The dimensions of the rotors are specified in the config; the
    surface material, position, orientation, and level of detail of the rotors are
    specified by separate parameters.

    Parameters
    ----------
    config : via_wind.config.Config
        Configuration namespace. Must contain "turbine" property with multiple
        required subproperties.
    surface_material : bpy.types.Material
        Material to be used for rendering the surface of the rotors. Typically
        from create_turbine_surface_material.
    distance_from_camera_m : float, optional
        Horizontal distance the rotors will be positioned away from the camera. By
        default this is set to 0m. The position_turbine function can be used to
        move the rotors for subsequent image rendering.
    rotation : tuple, optional
        Three element tuple defining rotation of the rotors relative to the the camera
        position. The elements of this tuple should be numeric (i.e., float or int)
        and in units of degrees. By default, this is set to VALID_ROTATIONS["FRONT"],
        which equals (0, 90, 0) and turns the rotors so the camera is looking at the
        front of the rotors.
    n_vertices : int, optional
        Number of vertices to used for creating the cylinder that represents the
        rotors. The smaller the number, the more jaggedy and less circular the rotors
        will appear. By default this is set to N_CYLINDER_VERTICES.

    Returns
    -------
    bpy_types.Object
        Returns Blender "mesh" Object shaped like a flattened cylinder, intended to
        represent turbine rotors (i.e., swept area).
    """
    rotor_radius = config.turbine.rotor_diameter_m * 0.5
    blade_radius = config.turbine.blade_chord_m * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=n_vertices)
    rotors = bpy.context.active_object
    rotors.name = "Rotors"
    rotors.location = (distance_from_camera_m, 0, config.turbine.hub_height_m)
    rotors.rotation_euler = np.radians(rotation)
    rotors.scale = (rotor_radius, rotor_radius, blade_radius)
    # add surface material
    rotors.data.materials.append(surface_material)

    return rotors


def create_tower(
    config, surface_material, distance_from_camera_m=0, n_vertices=N_CYLINDER_VERTICES
):
    """
    Create and configure the turbine "tower" to be used in the silouettes. The tower
    is created as an elongated, narrow cylinder with the round ends oriented
    perpendicular to the ground and the long axis vertically. The dimensions of the
    tower are specified in the config; the surface material, position, and level of
    detail of the rotors are specified by separate parameters.

    Parameters
    ----------
    config : via_wind.config.Config
        Configuration namespace. Must contain "turbine" property with multiple
        required subproperties.
    surface_material : bpy.types.Material
        Material to be used for rendering the surface of the rotors. Typically
        from create_turbine_surface_material.
    distance_from_camera_m : float, optional
        Horizontal distance the tower will be positioned away from the camera. By
        default this is set to 0m. The position_turbine function can be used to
        move the tower for subsequent image rendering.
    n_vertices : int, optional
        Number of vertices to used for creating the cylinder that represents the
        tower. The smaller the number, the more jaggedy and less circular the tower
        will appear. By default this is set to N_CYLINDER_VERTICES.

    Returns
    -------
    bpy_types.Object
        Returns Blender "mesh" Object shaped like an elongated cylinder, intended to
        represent turbine tower.
    """
    tower_radius = config.turbine.tower_diameter_m / 2.0
    tower_offset = 0.5 * config.turbine.hub_height_m
    bpy.ops.mesh.primitive_cylinder_add(vertices=n_vertices)
    tower = bpy.context.active_object
    tower.name = "Tower"
    tower.location = (distance_from_camera_m, 0, tower_offset)
    tower.scale = (tower_radius, tower_radius, tower_offset)
    # add surface material
    tower.data.materials.append(surface_material)

    return tower


def create_obstruction(
    surface_material,
    distance_from_camera_m=0,
    height_m=0,
    width_m=OBSTRUCTION_WIDTH_M,
    depth_m=OBSTRUCTION_DEPTH_M,
    rotation=OBSTRUCTION_ROTATION,
):
    """
    Create and configure the obstruction used to shield/hide parts of the turbine
    from view in the silouettes. The obstruction is created like a wide wall, standing
    perpendicular to the ground. The location and dimensions of the wall are specified
    by the input parameters.

    Parameters
    ----------
    surface_material : bpy.types.Material
        Material to be used for rendering the surface of the obstruction. Typically
        from create_obstruction_surface_material.
    distance_from_camera_m : float, optional
        Horizontal distance the obstruction will be positioned away from the camera. By
        default this is set to 0m. The position_obstruction function can be used to
        move the obstruction for subsequent image rendering.
    height_m : float, optional
        Height of the obstruction (i.e., bottom to top), by default 0. The
        position_obstruction function can be used to resize the obstruction height for
        subsequent image rendering.
    width_m : float, optional
        Width of the obstruction (i.e., left to right), by default OBSTRUCTION_WIDTH_M.
    depth_m : float, optional
        Depth of the obstruction (i.e., front to back), by default OBSTRUCTION_DEPTH_M.
    rotation : tuple, optional
        Three element tuple defining rotation of the obstruction relative to the camera
        position. The elements of this tuple should be numeric (i.e., float or int)
        and in units of degrees. By default, this is set to OBSTRUCTION_ROTATION,
        which equals (0, 90, 0) and turns the obstruction so the camera is looking at
        the front of the obstruction.

    Returns
    -------
    bpy_types.Object
        Returns Blender "mesh" Object shaped like a wide wall, intended to represent a
        visual obstruction shielding part of the turbine from view.
    """
    obstruction_vertical_offset = height_m / 2.0
    bpy.ops.mesh.primitive_plane_add()
    obstruction = bpy.context.active_object
    obstruction.name = "Obstruction"
    obstruction.location = (
        distance_from_camera_m,
        0,
        obstruction_vertical_offset,
    )
    obstruction.scale = (
        obstruction_vertical_offset,
        width_m * 0.5,
        depth_m * 0.5,
    )
    obstruction.rotation_euler = np.radians(rotation)
    # add surface material
    obstruction.data.materials.append(surface_material)

    return obstruction


def create_camera(config):
    """
    Create and configure the Blender "camera", including setting the camera lens size,
    sensor/film width, clip distances, location, height, and orientation.

    Parameters
    ----------
    config : via_wind.config.Config
        Configuration namespace. Must contain "camera" property with multiple
        subproperties.

    Returns
    -------
    bpy_types.Object
        Returns Blender "camera" Object
    """
    # define camera settings
    camera_data = bpy.data.cameras.new(name="Camera")
    # set to 50 mm lens with full frame
    camera_data.lens = config.camera.lens_mm
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.sensor_width = config.camera.film_width_mm
    # set the clipping distances for the camera based on the range of turbine distances
    # this is necessary to keep all turbines visible and also avoid rendering issues
    min_turbine_distance = min(config.turbine.distances_to_camera_m)
    max_turbine_distance = max(config.turbine.distances_to_camera_m)
    # do not start clipping any earlier than 100 meters or else rendering issues
    # may happen at larger distances
    if min_turbine_distance < MINIMUM_DISTANCE:
        raise ValueError(
            f"Invalid distance_to_camera: {min_turbine_distance}. "
            f"Distance to camera must be >= {MINIMUM_DISTANCE}."
        )
    camera_data.clip_start = CAMERA_CLIP_START
    camera_data.clip_end = max_turbine_distance + 1000

    # create and position the camera object
    camera = bpy.data.objects.new("Camera", camera_data)
    camera.location = (0, 0, config.camera.height_m)
    camera.rotation_euler = np.radians([90, 0, -90])

    return camera


def set_camera_tracking(camera, track_to_obj):
    """
    Sets a Blender camera to track the vertical location of the input Blender object.

    Parameters
    ----------
    camera : bpy_types.Object
        Blender "camera" Object
    track_to_obj : bpy_types.Object
        Blender object to which the camera will track
    """
    # set  camera to track rotors
    constraint = camera.constraints.new("TRACK_TO")
    constraint.target = track_to_obj
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"


def validate_rotation(rotation):
    """
    Checks that the input rotation is either one of the names of the well-known
    rotations (e.g., "FRONT", "DIAGONAL", "SIDE"), or is three element tuple.

    If a rotation name, the corresponding rotation angles are looked up and returned.

    If a tuple, does not check that the input values are numeric and in the expected
    range of values.

    Parameters
    ----------
    rotation : [str, tuple]
        Either the name of a rotation (e.g., "FRONT", "SIDE", "DIAGONAL") or a three-
        element tuple specifying the rotations around the X, Y, and Z axes in units
        of degrees.

    Returns
    -------
    tuple
        Three-element tuple specifying the rotations around the X, Y, and Z axes in
        units of degrees.

    Raises
    ------
    ValueError
        A ValueError will be raised if the input tuple does not have 3 elements.
    """
    rotation_angles = VALID_ROTATIONS.get(rotation, tuple(rotation))

    if not len(rotation_angles) == 3:
        raise ValueError(
            "Invalid input for rotation. Must either be a list/tuple with three "
            "numeric elements or one of the valid named rotations: "
            f"{list(VALID_ROTATIONS.keys())}."
        )

    return rotation_angles


def position_turbine(rotors, tower, config, distance_to_camera_m, rotation):
    """
    (Re)position the turbine, including both the rotors and the tower, to the specified
    distance from the camera and rotation angle.

    Parameters
    ----------
    rotors : bpy_types.Object
        Blender "mesh" object representing turbine rotors, typically created by
        create_rotors.
    tower : bpy_types.Object
        Blender "mesh" object representing turbine tower, typically created by
        create_tower.
    config : via_wind.config.Config
        Configuration namespace. Must contain "turbine" property with multiple
        subproperties.
    distance_to_camera_m : float, optional
        Horizontal distance the turbine will be positioned away from the camera.
    rotation : tuple, optional
        Three element tuple defining rotation of the turbine relative to the camera
        position. The elements of this tuple should be numeric (i.e., float or int)
        and in units of degrees.
    """
    rotation_angles = validate_rotation(rotation)

    # set the rotation/orientation of the rotors
    rotors.rotation_euler = np.radians(rotation_angles)

    # set the position of the tower
    tower.location.x = distance_to_camera_m

    # adjust the position of the rotors
    if rotation == "FRONT" or rotation_angles == VALID_ROTATIONS["FRONT"]:
        # move the rotor closer to the camera by the distance specified in the
        # config for the "rotor_overhang_m"
        rotors.location.x = distance_to_camera_m - config.turbine.rotor_overhang_m
        # center the rotor on centerline of the field of view (i.e., direction the
        # camera is looking)
        rotors.location.y = 0
    elif rotation == "SIDE" or rotation_angles == VALID_ROTATIONS["SIDE"]:
        # set the rotor distance so it is the same as the camera
        rotors.location.x = distance_to_camera_m
        # offset the turbine from the FOV centerline to the left by the distance
        # specified in the config for the "rotor_overhang_m"
        rotors.location.y = config.turbine.rotor_overhang_m
    elif rotation == "DIAGONAL" or rotation_angles == VALID_ROTATIONS["DIAGONAL"]:
        # turbine is turned at a 45 degree angle and it is "rotor_overhang_m"
        # this is a 45-45-90 right triangle, so the x and y offsets are equal to the
        # hypotenuse / sqrt(2) away
        off_dist = config.turbine.rotor_overhang_m / math.sqrt(2)
        # move forward by the offset distance
        rotors.location.x = distance_to_camera_m - off_dist
        # move off the centerline to the left by the offset distance
        rotors.location.y = off_dist
    else:
        # determining the rotor offset would require some trigonometry that hasn't
        # been implemented, so position the rotors like it is centered on the tower
        warnings.warn(
            "Input angle is not well-known. Rotor will be rotated but will not be "
            "offset from tower."
        )
        rotors.location.x = distance_to_camera_m
        rotors.location.y = 0


def position_obstruction(
    obstruction, config, height_m, turb_distance_to_camera_m, turb_rotation
):
    """
    (Re)position the obstruction to stay between the turbine and the camera based on the
    turbine distance away from the camera and rotation. Also resize the obstruction
    to the specified height.

    Parameters
    ----------
    obstruction : bpy_types.Object
        Blender "mesh" object representing obstruction, typically created by
        create_obstruction.
    config : via_wind.config.Config
        Configuration namespace. Must contain "turbine" property with multiple
        subproperties.
    height_m : float
        Height of the obstruction in meters.
    turb_distance_to_camera_m : float
        Horizontal distance the turbine is positioned away from the camera.
    turb_rotation : float
        Three element tuple defining rotation of the turbine relative to the camera
        position. The elements of this tuple should be numeric (i.e., float or int)
        and in units of degrees.
    """
    # set the height and vertical position of the obstruction
    obstruction.location.z = height_m * 0.5
    obstruction.scale.x = height_m * 0.5

    # adjust the distance to make sure it is in front of the turbine
    turb_rotation_angles = validate_rotation(turb_rotation)
    if turb_rotation == "FRONT" or turb_rotation_angles == VALID_ROTATIONS["FRONT"]:
        # turbine is facing front so move obstruction forward 1 m in front of the blades
        obstruction_distance = (
            turb_distance_to_camera_m
            - config.turbine.rotor_overhang_m
            - config.turbine.blade_chord_m * 0.5
            - 1
        )
    elif turb_rotation == "SIDE" or turb_rotation_angles == VALID_ROTATIONS["SIDE"]:
        # turbine is sideways so move obstruction forward the rotor radius plus 1m
        obstruction_distance = (
            turb_distance_to_camera_m - config.turbine.rotor_diameter_m * 0.5 - 1
        )
    elif (
        turb_rotation == "DIAGONAL"
        or turb_rotation_angles == VALID_ROTATIONS["DIAGONAL"]
    ):
        # turbine is at a 45 degree angle so move obstruction forward based on
        # rotor radius and offset from tower accounting for trig of 45-45-90 triangle
        # plus 1 m
        obstruction_distance = (
            turb_distance_to_camera_m
            - (config.turbine.rotor_diameter_m * 0.5 / math.sqrt(2))
            - (config.turbine.rotor_overhang_m / math.sqrt(2))
            - 1
        )
    else:
        # determining the obstruction offset would require some trigonometry that hasn't
        # been implemented, so position the obstruction as if the rotors are sideways
        warnings.warn(
            "Input angle is not well-known. Obstruction will be placed as if the "
            "rotors are sideways to ensure the turbine is obstructed."
        )
        # turbine is sideways so move obstruction forward the rotor radius plus 1m
        obstruction_distance = (
            turb_distance_to_camera_m - config.turbine.rotor_diameter_m * 0.5 - 1
        )

    obstruction.location.x = obstruction_distance


def render_image(scene, out_image, verbose=False):
    """
    Render a still image from the Blender scene. Output image is saved as a png
    file.

    Parameters
    ----------
    scene : bpy.types.Scene
        Blender scene to render.
    out_image : [str, pathlib.Path]
        Path to which the output image will be saved.
    verbose : bool, optional
        If True, show messages emitted by the Blender renderer. By default False,
        which hides these messages.
    """
    if isinstance(out_image, Path):
        out_image_fp = out_image.as_posix()
    else:
        out_image_fp = out_image
    scene.render.filepath = out_image_fp
    if verbose:
        bpy.ops.render.render(write_still=True)
    else:
        with CSilencer():
            bpy.ops.render.render(write_still=True)
