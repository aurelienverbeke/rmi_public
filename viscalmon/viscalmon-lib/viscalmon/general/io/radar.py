"""
Module for opening Rainbow and OPERA HDF5 files

Already tried to improve parallelism using:
- SharedMemory for returning data and nodata_mask arrays: overflowing shmmni limit
- xradar.io.backends.rainbow.open_rainbow_datatree instead of wradlib.io.rainbow.read_rainbow : 10x slower
- Not returning DataFrame for rows: not faster
- impa_unordered instead of map: no time gain
Nothing worked better.
"""





import datetime
import glob
import multiprocessing
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, TypedDict

import numpy as np
import pandas as pd
import wradlib
import xarray as xr
from dateutil import tz
from pyproj import CRS, Transformer

from viscalmon.general.io.utils import (
    acc_time_from_product_name,
    product_archive_folder,
    software_from_product_name,
)

MAX_NB_PROCESSES = 32
MAX_NB_WORKERS = 64
TYPES = {"moment":"str", "date":"str", "elevation":"Float32", "n_bins":"UInt16", "n_rays":"UInt16", "bin_res":"Float32", "freq":"Float32", "zdr_offset":"Float32", "phidp_offset":"Float32", "data":"object", "nodata_mask":"object"}
COLUMNS = list(TYPES.keys())





class SliceData(TypedDict):
    moment : str
    timestamp : str
    elevation : float
    n_bins : int
    n_rays : int
    bin_res : float
    freq : float
    zdr_offset : float
    phidp_offset : float
    data : np.ndarray[tuple[int, int], np.dtype[np.floating]]





def __open_rainbow_pandas_individual(rainbow_file : str) -> tuple[pd.DataFrame, float, float, float]:
    """
    Open one rainbow file.

    Parameters
    ----------
    rainbow_file : str
        File to open.

    Returns
    -------
        pandas.DataFrame
            All datasets (columns : moment, date, elevation, bins number, rays number, bin resolution(km), tx frequency(MHz), zdr offset (dB), phidp offset (deg), data, nodata mask) contained in the file.
        float
            Longitude in degrees.
        float
            Latitude in degrees.
        float
            Altitude in meters.

    See also
    --------
    wradlib.io.rainbow.read_rainbow
    """

    # Open file
    rainbow = wradlib.io.rainbow.read_rainbow(rainbow_file)



    datasets = pd.DataFrame(columns=COLUMNS)
    datasets = datasets.astype(TYPES)
    
    
    
    longitude = float(rainbow["volume"]["sensorinfo"]["lon"])
    latitude = float(rainbow["volume"]["sensorinfo"]["lat"])
    altitude = float(rainbow["volume"]["sensorinfo"]["alt"])
    n_elevations = int(rainbow["volume"]["scan"]["pargroup"]["numele"])



    if n_elevations == 1:
        # For treating all the same way
        slices = [ rainbow["volume"]["scan"]["slice"] ]
    else:
        slices = rainbow["volume"]["scan"]["slice"]


    for slice_dict in slices:
        data_dict = slice_dict["slicedata"]["rawdata"]

        # Get informations
        elevation = float(slice_dict["posangle"])
        min_value = float(data_dict["@min"])
        max_value = float(data_dict["@max"])
        depth = 2**int(data_dict["@depth"])
        gain = (max_value-min_value) / (depth-2)
        n_bins = int(data_dict["@bins"])
        n_rays = int(data_dict["@rays"])
        bin_res = float(slice_dict["rangestep"])
        if "gdrxtransmitfreq" in slice_dict:
            # real measured freq
            freq = float(slice_dict["gdrxtransmitfreq"])
        else:
            # theoretical freq from wavelength
            freq = 299792458 / float(rainbow["volume"]["sensorinfo"]["wavelen"])

        # Offsets depending on pulse width
        # Only for the old radars like Jabbeke for which we can select finite fixed values (usually 0.5us, 0.8us, 2us)
        # On new radars we can select the pulse width as we want -> same offset for all
        if "spbzdroffpw" in slice_dict:
            zdr_offsets = [ float(offset) for offset in slice_dict["spbzdroffpw"].split(" ") ]
            if "pw_index" in slice_dict:
                zdr_offset = zdr_offsets[int(slice_dict["pw_index"])]
            else:
                zdr_offset = zdr_offsets[0]
        else:
            zdr_offset = np.nan

        if "spbphidpoffpw" in slice_dict:
            phidp_offsets = [ float(offset) for offset in slice_dict["spbphidpoffpw"].split(" ") ]
            if "pw_index" in slice_dict:
                phidp_offset = phidp_offsets[int(slice_dict["pw_index"])]
            else:
                phidp_offset = phidp_offsets[0]
        else:
            phidp_offset = np.nan

        # Get dataset
        nodata_mask = data_dict["data"] == 0
        data = data_dict["data"]*gain + min_value

        # Put rays in the right order
        azimut_0 = 0.
        for rayinfo in slice_dict["slicedata"]["rayinfo"]:
            if rayinfo["@refid"] == "startangle":
                azimut_0 = rayinfo["data"][0] / 2**int(rayinfo["@depth"]) * 360
                break
        i_azimut_0 = int(np.floor(azimut_0 * n_rays / 360))
        data = np.roll(data, i_azimut_0, axis=0)
        nodata_mask = np.roll(nodata_mask, i_azimut_0, axis=0)
        
        filename = rainbow_file[rainbow_file.rfind("/")+1:]
        moment = filename[16:-4]
        date = filename[0:12]
        datasets.loc[len(datasets)] = [moment, date, elevation, n_bins, n_rays, bin_res, freq, zdr_offset, phidp_offset, data, nodata_mask]



    return datasets, longitude, latitude, altitude





def open_rainbow_pandas(rainbow_files : list[str]) -> tuple[pd.DataFrame, float, float, float]:
    """
    Open rainbow files.
    For one radar only.

    Parameters
    ----------
    rainbow_files : list of str
        Files to open.

    Returns
    -------
        pandas.DataFrame
            All datasets (columns : moment, date, elevation, bins number, rays number, bin resolution(km), tx frequency(MHz), zdr offset (dB), phidp offset (deg), data, nodata mask).
        float
            Longitude in degrees.
        float
            Latitude in degrees.
        float
            Altitude in meters.

    See also
    --------
    wradlib.io.rainbow.read_rainbow
    """

    datasets = pd.DataFrame(columns=COLUMNS)
    datasets = datasets.astype(TYPES)



    nb_processes = min(os.process_cpu_count(), MAX_NB_PROCESSES)
    with multiprocessing.Pool(processes=nb_processes) as pool:
        results = pool.map(__open_rainbow_pandas_individual, rainbow_files, chunksize=1)
        datasets = pd.concat([ result[0] for result in results ], ignore_index=True)
        longitude, latitude, altitude = (results[0][1], results[0][2], results[0][3])



    return datasets, longitude, latitude, altitude





def __open_rainbow_xarray_individual(rainbow_file : str) -> tuple[list[SliceData], float, float, float]:
    """
    Open one rainbow file.

    Parameters
    ----------
    rainbow_file : str
        File to open.

    Returns
    -------
    list(dict)
        All slices (columns : moment, timestamp, elevation, bins number, rays number, bin resolution(km), tx frequency(MHz), zdr offset (dB), phidp offset (deg), data) contained in the file.
    float
        Longitude in degrees.
    float
        Latitude in degrees.
    float
        Altitude in meters.

    See also
    --------
    wradlib.io.rainbow.read_rainbow
    """

    # Open file
    rainbow : dict = wradlib.io.rainbow.read_rainbow(rainbow_file)



    rows: list[SliceData] = []
    
    
    
    longitude = float(rainbow["volume"]["sensorinfo"]["lon"])
    latitude = float(rainbow["volume"]["sensorinfo"]["lat"])
    altitude = float(rainbow["volume"]["sensorinfo"]["alt"])
    n_elevations = int(rainbow["volume"]["scan"]["pargroup"]["numele"])



    if n_elevations == 1:
        # For treating all the same way
        slices : list[dict] = [ rainbow["volume"]["scan"]["slice"] ]
    else:
        slices : list[dict] = rainbow["volume"]["scan"]["slice"]


    for slice_dict in slices:
        data_dict : dict = slice_dict["slicedata"]["rawdata"]

        # Get informations
        elevation = float(slice_dict["posangle"])
        min_value = float(data_dict["@min"])
        max_value = float(data_dict["@max"])
        depth : int = 2**int(data_dict["@depth"])
        gain : float = (max_value-min_value) / (depth-2)
        n_bins = int(data_dict["@bins"])
        n_rays = int(data_dict["@rays"])
        bin_res = float(slice_dict["rangestep"])
        if "gdrxtransmitfreq" in slice_dict:
            # real measured freq
            freq = float(slice_dict["gdrxtransmitfreq"])
        else:
            # theoretical freq from wavelength
            freq = float(299792458 / float(rainbow["volume"]["sensorinfo"]["wavelen"]))

        # Offsets depending on pulse width
        # Only for the old radars like Jabbeke for which we can select finite fixed values (usually 0.5us, 0.8us, 2us)
        # On new radars we can select the pulse width as we want -> same offset for all
        if "spbzdroffpw" in slice_dict:
            zdr_offsets = [ float(offset) for offset in slice_dict["spbzdroffpw"].split(" ") ]
            if "pw_index" in slice_dict:
                zdr_offset = float(zdr_offsets[int(slice_dict["pw_index"])])
            else:
                zdr_offset = float(zdr_offsets[0])
        else:
            zdr_offset : float = np.nan

        if "spbphidpoffpw" in slice_dict:
            phidp_offsets = [ float(offset) for offset in slice_dict["spbphidpoffpw"].split(" ") ]
            if "pw_index" in slice_dict:
                phidp_offset = float(phidp_offsets[int(slice_dict["pw_index"])])
            else:
                phidp_offset = float(phidp_offsets[0])
        else:
            phidp_offset : float = np.nan

        # Get dataset
        nodata_mask : np.ndarray[tuple[int, int], np.dtype[np.bool_]] = data_dict["data"] == 0
        data : np.ndarray[tuple[int, int], np.dtype[np.floating]] = data_dict["data"]*gain + min_value
        data[nodata_mask] = np.nan

        # Put rays in the right order
        azimut_0 = 0.
        for rayinfo in slice_dict["slicedata"]["rayinfo"]:
            if rayinfo["@refid"] == "startangle":
                azimut_0 = float(rayinfo["data"][0] / 2**int(rayinfo["@depth"]) * 360)
                break
        i_azimut_0 = int(np.floor(azimut_0 * n_rays / 360))
        data : np.ndarray[tuple[int, int], np.dtype[np.floating]] = np.roll(data, i_azimut_0, axis=0)
        
        filename = rainbow_file[rainbow_file.rfind("/")+1:]
        moment = filename[16:-4]
        timestamp = filename[0:12]



        rows.append({
            "moment":       moment,
            "timestamp":    timestamp,
            "elevation":    elevation,
            "n_bins":       n_bins,
            "n_rays":       n_rays,
            "bin_res":      bin_res,
            "freq":         freq,
            "zdr_offset":   zdr_offset,
            "phidp_offset": phidp_offset,
            "data":         data
        })



    return rows, longitude, latitude, altitude





def open_rainbow_xarray(rainbow_files : list[str]) -> tuple[dict[tuple[str, float|int], xr.Dataset], float | None, float | None, float | None]:
    """
    Open rainbow files.
    For one radar only.

    Parameters
    ----------
    rainbow_files : list of str
        Files to open.

    Returns
    -------
    dict((string, float), xarray.Dataset)
        All data and metadata coming from all files.

        Key: (timestamp, elevation)

        Value: xarray.Dataset with:
        - Coordinates: ray and bin indexes
        - Attributes : timestamp, elevation, bin resolution (*bin_res*), tx frequency (*freq*), Zdr Ravis offset (*zdr_offset*), PhiDP Ravis offset (*phidp_offset*)
        - Variables : moments by moment name
    float
        Longitude in degrees.
    float
        Latitude in degrees.
    float
        Altitude in meters.

    See also
    --------
    wradlib.io.rainbow.read_rainbow

    xarray.Dataset
    """



    # Open files in parallel
    nb_workers = min(os.process_cpu_count(), MAX_NB_WORKERS)
    with ThreadPoolExecutor(max_workers=nb_workers) as executor:
        results = list(executor.map(__open_rainbow_xarray_individual, rainbow_files, chunksize=max(len(rainbow_files)//nb_workers, 1)))
    
    if len(results) == 0:
        return {}, None, None, None
    
    # Merge all scans
    # In results scans are grouped by files
    all_slices = []
    for result in results:
        slices, longitude, latitude, altitude = result
        all_slices.extend(slices)
    
    # Group by (timestamp, elevation)
    datasets = {}
    for s in all_slices:
        key = (s["timestamp"], s["elevation"])
        if key not in datasets:
            datasets[key] = xr.Dataset(
                coords={
                    "ray": np.arange(s["n_rays"]),
                    "bin": np.arange(s["n_bins"]),
                },
                attrs={
                    "timestamp":    datetime.datetime.strptime(s["timestamp"], "%Y%m%d%H%M").replace(tzinfo=datetime.timezone.utc),
                    "elevation":    s["elevation"],
                    "bin_res":      s["bin_res"],
                    "freq":         s["freq"],
                    "zdr_offset":   s["zdr_offset"],
                    "phidp_offset": s["phidp_offset"],
                }
            )

        # Each moment is a variable in the dataset
        # Normally, bin_res, freq, zdr_offset and phidp_offset don't change for a same scan between two moments
        try:
            if (s["bin_res"] != datasets[key].attrs["bin_res"]):
                # Really a problem if changes
                # For other attributes, not that serious
                raise ValueError("Not same bin resolution.")
            datasets[key][s["moment"]] = (["ray", "bin"], s["data"])
        except Exception:
            # If data matrix size is different between moments, forget it
            print(f"Error with key {key}, passing")



    return datasets, float(longitude), float(latitude), float(altitude)





def __open_hdf_individual(params : tuple[str, Literal["rainbow", "radqpe2"]]) \
        -> tuple[datetime.datetime, int, int, float, float, datetime.timedelta, \
                    np.ndarray[tuple[int, int], np.dtype[np.floating]], \
                    np.ndarray[tuple[int, int], np.dtype[np.floating]], \
                    np.ndarray[tuple[int, int], np.dtype[np.floating]], \
                    str]:
    """
    Open one HDF5 file.
    **Only handles Rainbow and RMI QPE rainfall rate and accumulation files.**

    Parameters
    ----------
    hdf_file : str
        File to open.
    
    software : {'rainbow', 'radqpe2'}
        Software used to produce the file.

    Returns
    -------
    timestamp : datetime.datetime
        Validity timestamp of the data.
    
    n_x_pixels : int
        Horizontal number of pixels.

    n_y_pixels : int
        Vertical number of pixels.

    x_pixel_res : float
        Horizontal resolution of a pixel in kilometers.

    y_pixel_res : float
        Vertical resolution of a pixel in kilometers.

    acc_time : datetime.timedelta
        Accumulation duration. `None` in rainfall rate.

    data : np.ndarray
        Data array.
    
    lons : np.ndarray
        Longitudes of each pixel.

    lats : np.ndarray
        Latitudes of each pixel.
    
    proj : str
        Projection string.

    See also
    --------
    wradlib.io.hdf.read_opera_hdf5

    pyproj.Transformer

    pyproj.CRS
    """

    # Get function parameters
    hdf_file, software = params



    # Open file
    hdf : dict = wradlib.io.hdf.read_opera_hdf5(hdf_file)



    # Prof definition in /where
    proj : str = hdf["where"]["projdef"].decode("UTF-8")
    ul_lon = float(hdf["where"]["UL_lon"])
    ul_lat = float(hdf["where"]["UL_lat"])




    # Rainbow
    if software == "rainbow":
        gain = float(hdf["dataset1/what"]["gain"])
        offset = float(hdf["dataset1/what"]["offset"])
        nodata = float(hdf["dataset1/what"]["nodata"])
        undetect = float(hdf["dataset1/what"]["undetect"])
        n_x_pixels = int(hdf["where"]["xsize"])
        n_y_pixels = int(hdf["where"]["ysize"])
        x_pixel_res = float(hdf["where"]["xscale"])
        y_pixel_res = float(hdf["where"]["yscale"])
        qpe_type : str = hdf["dataset1/what"]["quantity"].decode("UTF-8").lower()




    # RADQPE2
    elif software == "radqpe2":
        if "gain" in hdf["dataset1/what"]:
            gain = float(hdf["dataset1/what"]["gain"])
            offset = float(hdf["dataset1/what"]["offset"])
            nodata = float(hdf["dataset1/what"]["nodata"])
        else:
            gain = 1.
            offset = 0.
            nodata = None
        undetect = None
        qpe_type : str = hdf["dataset1/data1/what"]["quantity"].decode("UTF-8").lower()
        n_x_pixels = int(hdf["dataset1/where"]["xsize"])
        n_y_pixels = int(hdf["dataset1/where"]["ysize"])
        x_pixel_res = float(hdf["dataset1/where"]["xscale"])
        y_pixel_res = float(hdf["dataset1/where"]["yscale"])
    


    # Another software, crash
    else:
        raise ValueError("Wrong software.")



    # Time dimension
    timestamp = datetime.datetime.strptime(hdf["what"]["date"].decode("UTF-8") + hdf["what"]["time"].decode("UTF-8")[:4], "%Y%m%d%H%M").replace(tzinfo=datetime.timezone.utc)
    if software == "rainbow" and qpe_type == "rate":
        # For RR, Rainbow sets timestamp as the begin of the 5min range
        timestamp += datetime.timedelta(0, 0, 0, 0, 5)
    
    if qpe_type == "acrr":
        start_timestamp = datetime.datetime.strptime(hdf["dataset1/what"]["startdate"].decode("UTF-8") + hdf["dataset1/what"]["starttime"].decode("UTF-8")[:4], "%Y%m%d%H%M").replace(tzinfo=datetime.timezone.utc)
        acc_time = timestamp - start_timestamp
    else:
        acc_time = datetime.timedelta()
    


    # Convert matrix to real values
    if nodata is not None:
        nodata_mask : np.ndarray[tuple[int, int], np.dtype[np.bool_]] = hdf["dataset1/data1/data"] == nodata
    
    if undetect is not None:
        undetect_mask : np.ndarray[tuple[int, int], np.dtype[np.bool_]] = (hdf["dataset1/data1/data"] == undetect)

    data  : np.ndarray[tuple[int, int], np.dtype[np.floating]] = hdf["dataset1/data1/data"]*gain + offset

    if nodata is not None:
        data[nodata_mask] = np.nan
    if undetect is not None:
        data[undetect_mask] = np.nan
    


    # Calculate WGS84 lat/lon coordinates for each pixel
    hdf_crs = CRS.from_proj4(proj)
    latlon_to_proj = Transformer.from_crs(4326, hdf_crs, always_xy=True)
    proj_to_latlon = Transformer.from_crs(hdf_crs, 4326, always_xy=True)

    ul_x, ul_y = latlon_to_proj.transform(ul_lon, ul_lat)
    x : np.ndarray[tuple[int], np.dtype[np.floating]] = ul_x + (np.arange(n_x_pixels) + 0.5) * x_pixel_res
    y : np.ndarray[tuple[int], np.dtype[np.floating]] = ul_y - (np.arange(n_y_pixels) + 0.5) * y_pixel_res

    xs, ys = np.meshgrid(x, y)

    lons, lats = proj_to_latlon.transform(xs, ys)



    return timestamp, n_x_pixels, n_y_pixels, x_pixel_res, y_pixel_res, acc_time, data, lons, lats, proj





def open_hdf(hdf_files : list[str], software : Literal["rainbow", "radqpe2"]) -> dict[datetime.datetime, xr.DataArray]:
    """
    Open HDF5 files.
    For one radar and data type only.
    **Only handles Rainbow and RMI QPE rainfall rate and accumulation files.**

    Parameters
    ----------
    hdf_files : list of str
        Files to open.
    
    software : {'rainbow', 'radqpe2'}
        Software used to produce the file.

    Returns
    -------
    dict(datetime.datetime, xarray.DataArray)
        All data and metadata coming from all files.

        Key: timestamp

        Value: xarray.DataArray with:
        - Coordinates: lons and lats of each pixel
        - Attributes : timestamp, horizontal number of pixels (*n_x_pixels*), vertical number of pixels (*n_y_pixels*), horizontal pixel resolution (*x_pixel_res*), vertical pixel resolution (*y_pixel_res*), accumulation time (*acc_time*, `None` in rainfall rate) and projection string (*proj)
        - Data : data matrix

    See also
    --------
    wradlib.io.rainbow.read_rainbow

    xarray.Dataset
    """



    # Open files in parallel
    nb_workers = min(os.process_cpu_count(), MAX_NB_WORKERS)
    with ThreadPoolExecutor(max_workers=nb_workers) as executor:
        results = list(executor.map(__open_hdf_individual, zip(hdf_files, [software]*len(hdf_files)), chunksize=max(len(hdf_files)//nb_workers, 1)))
    
    # Group by timestamp
    datasets = {}
    for result in results:
        timestamp, n_x_pixels, n_y_pixels, x_pixel_res, y_pixel_res, acc_time, data, lons, lats, proj = result
        key = timestamp
        if key not in datasets:
            datasets[key] = xr.DataArray(
                data=data,
                dims=["x", "y"],
                coords={
                    "lon": (["x", "y"], lons),
                    "lat": (["x", "y"], lats),
                },
                attrs={
                    "timestamp": timestamp,
                    "acc_time": acc_time,
                    "n_x_pixels": n_x_pixels,
                    "n_y_pixels": n_y_pixels,
                    "x_pixel_res": x_pixel_res,
                    "y_pixel_res": y_pixel_res,
                    "proj": proj
                }
            )
        else:
            raise KeyError("Two files have the same timestamp.")



    return datasets





def get_files_names(product_name : str, begin_timestamp : datetime.datetime, end_timestamp : datetime.datetime, \
                    radar : str | None = None, \
                    minutes_to_keep : list[int] | None = None, \
                    hours_to_keep : list[int] | None = None) \
                        -> list[str]:
    """
        Gives the files names associated to a product and eventually a radar, between two (included) timestamps.

        Parameters
        ----------
        product_name : str
            See `product_archive_folder`.
            `'vol'` and `'azi'` should be extended with moments such as `'vol:ZDR,dBZ'`
        
        begin_timestamp : datetime.datetime
            Begin timestamp.

        end_timestamp : datetime.datetime
            Begin timestamp.
        
        radar : str, optional
            See `product_archive_folder`.
        
        minutes_to_keep : list of str, optional
            List of the files timestamps minutes to keep. None or nothing for no filtering.
        
        hours_to_keep : list of str, optional
            List of the files timestamps hours to keep **in local time, not file name**. None or nothing for no filtering.

        Returns
        -------
        list of str
            Files names.

        Raises
        ------
        ValueError
            If the product or radar name is unknown, or if the end timestamp is before the begin timestamp.

    """

    if begin_timestamp > end_timestamp:
        raise ValueError("Wrong order in timestamps.")



    # Convert default value to keep all timestamps
    if minutes_to_keep is None:
        minutes_to_keep = list(range(60))
    if hours_to_keep is None:
        hours_to_keep = list(range(24))
    


    acc_time = acc_time_from_product_name(product_name)
    software = software_from_product_name(product_name)



    # Rainbow rain rates are timestamped at the beginning of the 5 minutes
    if software == "rainbow" and acc_time == datetime.timedelta() and product_name[:3] not in ["vol", "azi"]:
        begin_timestamp += datetime.timedelta(minutes=5)
        end_timestamp += datetime.timedelta(minutes=5)
    
    
    
    # Get all files names between both timestamps respecting minutes_to_keep and hours_to_keep
    files = []

    from_zone = tz.gettz("UTC")
    to_zone = tz.gettz("Europe/Brussels")
    
    date = begin_timestamp.date()
    while date <= end_timestamp.date():
        # Get real folder name for pattern
        # Expands ? and *
        folder_pattern = product_archive_folder(product_name, date, radar)
        resolved_folders = glob.glob(folder_pattern)

        for folder in resolved_folders:
            if not folder.endswith("/"):
                folder += "/"

            files_in_folder = glob.glob(pathname="*", root_dir=folder)
            
            # If vertical or volumic data, only keep specified moments
            if product_name[:3] in ["vol", "azi"]:
                extension = product_name[:3]
                try:
                    moments = product_name.split(":")[1].split(",")
                    pattern = re.compile(rf"^.{{16}}({"|".join(moments)})\.{extension}$")
                except IndexError:
                    pattern = re.compile(rf"\.{extension}$")

            for file in files_in_folder:
                timestamp = datetime.datetime.strptime(file[:12], "%Y%m%d%H%M").replace(tzinfo=datetime.timezone.utc)
                # For getting local time hours
                local_timestamp = timestamp.replace(tzinfo=from_zone).astimezone(to_zone)
                if begin_timestamp <= timestamp <= end_timestamp \
                        and local_timestamp.hour in hours_to_keep \
                        and int(file[10:12]) in minutes_to_keep \
                        and (product_name[:3] not in ["vol", "azi"] or pattern.search(file)):
                    files.append(folder + file)
            
        date += datetime.timedelta(days=1)
    
    return files