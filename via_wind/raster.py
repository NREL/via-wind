# -*- coding: utf-8 -*-
"""
raster module
"""
import math

import rasterio
from osgeo import gdal
from osgeo_utils.gdal_merge import gdal_merge
from lxml import etree
import geopandas as gpd
import pyproj
from shapely import geometry
import numpy as np

# stop to_crs() bugs
pyproj.network.set_network_enabled(active=False)

gdal.UseExceptions()

GEOTIFF_PROFILE = {
    "driver": "GTiff",
    "dtype": "float32",
    "count": 1,
    "blockxsize": 2048,
    "blockysize": 2048,
    "tiled": True,
    "interleave": "band",
    "compress": "deflate",
    "nodata": None,
    "width": None,
    "height": None,
    "crs": None,
    "transform": None,
    "BIGTIFF": "YES"
}

VALID_DTYPES = (
    "int8",
    "uint8",
    "int16",
    "uint16",
    "int32",
    "uint32",
    "float32",
    "float64",
)

VALID_CRS_UNITS = ["metre", "meter", "m"]


def get_raster_info(raster_src):
    """
    Get metadata information from a source raster dataset.

    Parameters
    ----------
    raster_src : [pathlib.Path, str]
        Path to raster dataset.

    Returns
    -------
    dict
        Returns a dictionary of the format {"crs": rasterio.crs.CRS,
        "resolution": float, "shape": tuple, "profile": dict), where the values
        are metadata from the source raster.

    Raises
    ------
    ValueError
        A ValueError will be raised if the raster has different horizontal and vertical
        resolutions.
    """
    with rasterio.open(raster_src) as rast:
        crs = rast.crs
        resolution = rast.res
        shape = rast.shape
        profile = rast.profile

    if not math.isclose(resolution[0], resolution[1], abs_tol=0.001):
        raise ValueError(
            "Input raster resolution is not the same in the X and Y dimensions: "
            f"X={resolution[0]}, Y={resolution[1]}"
        )

    values = {
        "crs": crs,
        "resolution": resolution[0],
        "shape": shape,
        "profile": profile,
    }
    return values


def validate_crs_units(crs):
    """
    Validate that the CRS is in linear units of meters.

    Parameters
    ----------
    crs : rasterio.crs.CRS
        Rasterio Coordinate reference system

    Raises
    ------
    ValueError
        A ValueError will be raised if the input CRS is not in linear units of meters
        or one of its known aliases.
    """
    if crs.linear_units.lower() not in VALID_CRS_UNITS:
        raise ValueError(
            f"Input raster CRS must have one of the following linear units: "
            f"{VALID_CRS_UNITS}. Found '{crs.linear_units}' instead."
        )


def save_to_geotiff(array, affine, crs, out_tif, nodata_value=None, tags=None):
    """
    Save an array to a GeoTiff.

    Parameters
    ----------
    array : numpy.ndarray
        Two dimensional Numpy array
    affine : affine.Affine
        Affine describing the raster resolution and origin.
    crs : rasterio.crs.CRS
        Rasterio Coordinate Reference System for the output raster.
    out_tif : [pathlib.Path, str]
        Path to which the GeoTiff will be saved
    nodata_value : [float, int], optional
        Value that will be assigned to NoData in the output raster, by default None.
    tags: [dict, None], optional
        If specified, key-value pairs will be written as metadata to the output
        GeoTiff.

    Raises
    ------
    TypeError
        A TypeError will be raised if the input array is not a valid data type for
        writing by rasterio.
    """
    if not array.dtype.name in VALID_DTYPES:
        raise TypeError(
            f"Invalid array dtype: {array.dtype}. Valid types are: {VALID_DTYPES}."
        )

    out_profile = GEOTIFF_PROFILE.copy()
    out_profile["nodata"] = nodata_value
    out_profile["width"] = array.shape[1]
    out_profile["height"] = array.shape[0]
    out_profile["crs"] = crs
    out_profile["transform"] = affine
    out_profile["dtype"] = array.dtype.name

    with rasterio.open(out_tif, "w", **out_profile) as out_rast:
        out_rast.write(array, 1)
        if tags is not None:
            out_rast.update_tags(**tags)


def create_vrt(tif_dir_path, out_vrt_path, pattern="*.tif"):
    """
    Constructs a VRT referencing all of the GeoTiffs in the specified directory.

    Parameters
    ----------
    tif_dir_path : pathlib.Path
        Path to folder containing GeoTiffs. Folder will be searched recursively.
    out_vrt_path : pathlib.Path
        Path for output VRT.
    pattern : string
        Optional glob pattern used to search for tifs. By default, all tifs will be
        returned.

    Returns
    -------
    osgeo.gdal.Dataset
        GDAL Dataset containing VRT results.

    Raises
    ------
    FileNotFoundError
        A FileNotFoundError will be raised if no tifs can be found in the input
        directory.
    """

    tifs = [t.as_posix() for t in tif_dir_path.rglob(pattern)]
    if len(tifs) == 0:
        raise FileNotFoundError(f"No tifs found in {tif_dir_path}")

    vrt = gdal.BuildVRT(out_vrt_path.as_posix(), tifs)
    vrt.FlushCache()

    return vrt


def merge_tifs(tifs_path, out_tif_path, pattern="*.tif"):
    """
    Merge the geotiffs in an input directory to a single GeoTiff.

    Parameters
    ----------
    tifs_path : pathlib.Path
        Path to directory containing GeoTiffs
    out_tif_path : pathlib.Path
        Path for output merged GeoTiff
    """

    args = [
        "",
        "-o",
        out_tif_path.as_posix(),
        "-co",
        "COMPRESS=DEFLATE",
        "-co",
        "BIGTIFF=YES",
        "-quiet",
    ]
    tifs = [t.as_posix() for t in tifs_path.rglob(pattern)]
    args.extend(tifs)
    gdal_merge(args)


def read_vrt_sources(vrt_path):
    """
    Reads a VRT file, parses the source rasters, and constructs an index of the source
    raster bounds in pixel units relative to the full VRT extent.

    Parameters
    ----------
    vrt_source : [str, pathlib.Path]
        Path to source VRT file.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame where each row contains information about a source raster included
        in the VRT, including the raster filepath and its bounds in pixel coordinates
        relative to the VRT extent as both a tuple and a geometry.
    """

    vrt_tree = etree.parse(vrt_path)
    vrt_root = vrt_tree.getroot()
    raster_sources = vrt_root.findall(".//SimpleSource")
    vrt_source_info = []
    for raster_source in raster_sources:
        src_file = raster_source.findall("SourceFilename")[0].text
        dst_rect = {k: int(v) for k, v in raster_source.findall("DstRect")[0].items()}
        bounds = [
            dst_rect["xOff"],
            dst_rect["yOff"],
            dst_rect["xOff"] + dst_rect["xSize"],
            dst_rect["yOff"] + dst_rect["ySize"],
        ]
        vrt_source_info.append(
            {"src_file": src_file, "bounds": bounds, "geometry": geometry.box(*bounds)}
        )
    vrt_sources_df = gpd.GeoDataFrame(vrt_source_info, geometry="geometry")

    return vrt_sources_df


def mosaic_block(
    vrt_sources_df, full_profile, out_path, col_offset, row_offset, block_size
):
    """
    Typically used on a VRT, this function mosaics a block (i.e., square section)
    of the VRT, including the relevant source rasters that intersect the block
    (either partially or fully).

    Parameters
    ----------
    vrt_sources_df : geopandas.GeoDataFrame
        GeoDataFrame containing information about the source rasters to mosaic
        and their bounds relative to the full VRT. Typically from read_vrt_sources().
    full_profile : dict
        Rasterio Profile of the full VRT.
    out_path : pathlib.Path
        Output path to which the mosaicked block will be saved. The output raster will
        be a geotiff and named dynamically based on the row and column offsets.
    col_offset : int
        Column offset where the block starts, relative to the top left of the VRT.
    row_offset : int
        Row offset where the block starts, relative to the top left of the VRT.
    block_size : int
        Size of the block to mosaic.
    """

    out_tif_path = out_path.joinpath(f"block_{row_offset}_{col_offset}.tif")

    block_bounds = [
        col_offset,
        row_offset,
        min(col_offset + block_size, full_profile["width"]),
        min(row_offset + block_size, full_profile["height"]),
    ]
    # add one extra row because of weird artifact that happens in the final row
    # we trim this row off before writing the final output
    block_bounds[3] += 1

    width = block_bounds[2] - block_bounds[0]
    height = block_bounds[3] - block_bounds[1]

    block_box = geometry.box(*block_bounds)
    src_files_in_block = vrt_sources_df[vrt_sources_df.intersects(block_box)][
        "src_file"
    ]

    block_window = rasterio.windows.Window(
        col_offset, row_offset, width=width, height=height
    )
    block_transform = rasterio.windows.transform(
        block_window, full_profile["transform"]
    )
    block_window_bounds = rasterio.windows.bounds(
        block_window, full_profile["transform"]
    )
    block_window_extent = geometry.box(*block_window_bounds)

    block_array = np.zeros((height, width), dtype=full_profile["dtype"])
    for src_file_in_block in src_files_in_block:
        with rasterio.open(src_file_in_block, "r") as s:
            src_extent = geometry.box(*list(s.bounds))
            read_bbox = src_extent.intersection(block_window_extent)

            src_window = rasterio.windows.from_bounds(
                *read_bbox.bounds, transform=s.transform
            ).round_lengths()
            src_array = s.read(1, window=src_window)

            add_window = rasterio.windows.from_bounds(
                *read_bbox.bounds, transform=block_transform
            ).round_lengths()

            add_window_fix = rasterio.windows.Window(
                col_off=add_window.col_off,
                row_off=add_window.row_off,
                width=src_array.shape[1],
                height=src_array.shape[0],
            )

            row_start = int(add_window_fix.row_off)
            row_stop = row_start + src_array.shape[0]
            col_start = int(add_window_fix.col_off)
            col_stop = col_start + src_array.shape[1]
            block_array[row_start:row_stop, col_start:col_stop] += src_array

    out_profile = full_profile.copy()
    out_profile.update(
        {
            "driver": "GTiff",
            "nodata": None,
            "transform": block_transform,
            "width": width,
            "height": height - 1,
        }
    )

    with rasterio.open(out_tif_path, "w", **out_profile) as out_rast:
        out_rast.write(block_array[:-1, :], 1)
