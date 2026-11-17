import datetime
import json
import logging
import multiprocessing
import os
from importlib.resources import files as importfiles
from typing import Any, Literal

import cv2
import numpy as np
import pandas as pd
import wradlib
import xarray
from scipy.interpolate import griddata

from viscalmon.general.io.radar import open_rainbow_xarray

MAX_NB_PROCESSES = 64
TYPES = {"radar":"str", "moment":"str", "date":"str", "elevation":"str", "file":"str", "max_range":"Float32"}
COLUMNS = list(TYPES.keys())





# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)


    
    
    
def sort_function(col):
    if col.name == "elevation":
        return col.astype("Float32")
    else:
        return col.str.lower()





def create_ppi(args: tuple[pd.DataFrame, Any, str, str, float, float, float, xarray.Dataset]):
    df_info, colormaps, folder, radar, longitude, latitude, alt, dataset = args
    
    results = []
        
    for moment, data_moment in dataset.data_vars.items():
        str_timestamp = dataset.attrs["timestamp"].strftime("%Y%m%d%H%M")
        elevation = dataset.attrs["elevation"]
        

        # PPI already created
        if not df_info[(df_info["radar"]==radar) 
                        & (df_info["moment"]==moment)
                        & (df_info["date"]==str_timestamp)
                        & (df_info["elevation"]==f"{elevation:.1f}")]\
                .empty:
            continue



        # Get data matrix and its shape
        data = data_moment.values
        shape = data.shape
        bin_res = dataset.attrs["bin_res"]
        n_rays = shape[0]
        n_bins = shape[1]



        max_range = (n_bins-1/2)*bin_res
        
        ranges = np.linspace(bin_res/2, max_range, n_bins)
        azimuts = np.arange(0, 360, 360/n_rays)

        
        
        # Cartesian grid
        cartesian_ranges = np.linspace(-max_range, max_range, 2*n_bins)
        cartesian_grid_x, cartesian_grid_y = np.meshgrid(cartesian_ranges, -cartesian_ranges)
        cartesian_grid_distances = np.sqrt(cartesian_grid_x**2 + cartesian_grid_y**2)

        
        
        # Polar coordinates in cartesian grid
        polar_grid_ranges, polar_grid_azimuts = np.meshgrid(ranges, azimuts)
        xyz, _ = wradlib.georef.polar.spherical_to_xyz(polar_grid_ranges, polar_grid_azimuts, elevation, (longitude, latitude, alt))
        x_polar = xyz[..., 0]
        y_polar = xyz[..., 1]

        # Convert meters to km
        x_polar /= 1000
        y_polar /= 1000

        
        
        # Interpolation on cartesian grid
        data_cartesian = griddata(np.column_stack([x_polar.flatten(), y_polar.flatten()]),
                                    data.flatten(),
                                    np.column_stack([cartesian_grid_x.flatten(), cartesian_grid_y.flatten()]),
                                    method="nearest")
        nan_mask_cartesian = np.isnan(data_cartesian) | (cartesian_grid_distances.flatten()>max_range)

    
        
        # Create and save PPI
        ppi = np.zeros((*data_cartesian.shape, 4), dtype=np.uint8)

        for group in colormaps[moment]:
            if group["bounds"] == "missing":
                selected_pixels = nan_mask_cartesian
            else:
                selected_pixels = (group["bounds"][0]<data_cartesian) & (data_cartesian<=group["bounds"][1]) & ~nan_mask_cartesian
            ppi[selected_pixels] = [group["color"][2], group["color"][1], group["color"][0], group["color"][3]] # OpenCV working in BGRA

        base_filename = radar + "_" + str_timestamp + "_" + str(int(elevation*10)) + "_" + moment + ".png"
        complete_filename = folder + "/" + base_filename
        cv2.imwrite(complete_filename, np.reshape(ppi, (2*n_bins, 2*n_bins, 4)), [cv2.IMWRITE_PNG_COMPRESSION, 9])
        
        
        results.append([moment, str_timestamp, elevation, base_filename, dataset.attrs["bin_res"]*shape[1]])
         
            
            
    return results





def create_azi_dist(args : tuple[pd.DataFrame, Any, str, str, xarray.Dataset]):
    df_info, colormaps, folder, radar, dataset = args

    results = []
    
    for moment, data_moment in dataset.data_vars.items():
        str_timestamp = dataset.attrs["timestamp"].strftime("%Y%m%d%H%M")
        elevation = dataset.attrs["elevation"]

        # PPI already created
        if not df_info[(df_info["radar"]==radar) 
                        & (df_info["moment"]==moment)
                        & (df_info["date"]==str_timestamp)
                        & (df_info["elevation"]==f"{elevation:.1f}")]\
                .empty:
            continue

        # Get data matrix and its shape
        data = data_moment.values
        shape = data.shape

        # Create and save azimut-distance image
        azi_dist = np.zeros((*shape, 4), dtype=np.uint8)

        nan_mask = np.isnan(data)
        for group in colormaps[moment]:
            if group["bounds"] == "missing":
                selected_pixels = nan_mask
            else:
                selected_pixels = (group["bounds"][0]<data) & (data<=group["bounds"][1]) & ~nan_mask
            azi_dist[selected_pixels] = [group["color"][2], group["color"][1], group["color"][0], group["color"][3]] # OpenCV working in BGRA

        base_filename = radar + "_" + str_timestamp + "_" + str(int(elevation*10)) + "_" + moment + ".png"
        complete_filename = folder + "/" + base_filename
        cv2.imwrite(complete_filename, azi_dist, [cv2.IMWRITE_PNG_COMPRESSION, 9])

        results.append([moment, str_timestamp, elevation, base_filename, dataset.attrs["bin_res"]*shape[1]])
 
    
    
    return results





def create_images(radar : str, start_timestamp : datetime.datetime, end_timestamp : datetime.datetime, files : list[str], mode : Literal["ppi", "azidist"]):
    """
        Creates PPI or azimut-distance plot from raw data

        Parameters :
            radar (str) : name of the radar
            start_date, end date (str) : start and end dates in YYYYMMDDHHMM format
            files (list(str)) : files to transform in images
            mode (str:ppi|azidist) : create either PPI or azimut-distances plot from data
    """
    
    data, longitude, latitude, alt = open_rainbow_xarray(files)

    if alt is None or longitude is None or latitude is None:
        logger.error("Missing geographical metadata.")
        raise ValueError("Missing geographical metadata.")
    else:
        alt = float(alt)
        longitude = float(longitude)
        latitude = float(latitude)



    # folder where put ppis and info csv
    if mode=="ppi":
        images_folder = os.environ["DIR_PPI"]
    else:
        images_folder = os.environ["DIR_AZI_DIST"]
    images_folder += f"{start_timestamp.strftime("%Y%m%d%H%M")}-{end_timestamp.strftime("%Y%m%d%H%M")}/"
    if not os.path.isdir(images_folder):
        os.mkdir(images_folder, 0o755)
    logger.debug(f"Images folder: {images_folder}")



    info_filename = f"{images_folder}info.csv"
    if os.path.isfile(info_filename) and os.path.getsize(info_filename)>0:
        logger.debug("Info CSV already existing it.")
        df_info = pd.read_csv(info_filename, dtype=TYPES)
    else:
        # no existing info csv file, create it
        logger.debug("Info CSV not existing, creating it.")
        df_info = pd.DataFrame(columns=COLUMNS)
        df_info = df_info.astype(TYPES)



    # clean PPIs folder
    filenames = os.listdir(images_folder)

    # remove rows in info csv if the associated image doesn't exists
    rows_to_delete = [ i for i, filename in df_info["file"].items() if filename not in filenames ]
    logger.info(f"Files referenced in info csv and that don't exist: {df_info["file"].to_numpy()[rows_to_delete]}")
    df_info.drop(rows_to_delete)

    # remove all files that are neither info.csv or ppis referenced in info.csv
    files_to_keep = ["info.csv"] + list(df_info["file"])
    for filename in os.listdir(images_folder):
        if filename not in files_to_keep:
            logger.info(f"Files not reference, will be deleted: {filename}")
            os.remove(images_folder+filename)

    
    
    # open color maps for all subprocesses
    with importfiles("viscalmon.viewer").joinpath("colormaps.json").open("r") as f_colormaps:
        colormaps = json.load(f_colormaps)


    
    # Create pngs in parallel
    nb_processes = min(os.process_cpu_count(), MAX_NB_PROCESSES)
    results = []
    with multiprocessing.Pool(processes=nb_processes) as pool:
        if mode=="ppi":
            for result in pool.imap_unordered(create_ppi, [ (df_info, colormaps, images_folder, radar, longitude, latitude, alt, dataarray) for dataarray in data.values()], chunksize=max(len(data)//nb_processes, 1)):
                results.extend([[radar] + row for row in result])
        else:
            for result in pool.imap_unordered(create_azi_dist, [ (df_info, colormaps, images_folder, radar, dataarray) for dataarray in data.values()], chunksize=max(len(data)//nb_processes, 1)):
                results.extend([[radar] + row for row in result])
    df_info = pd.concat(
        [df_info, pd.DataFrame(results, columns=df_info.columns)],
        ignore_index=True
    )



    df_info.sort_values(by=["radar", "moment", "elevation", "date"], inplace=True, key=sort_function)
    df_info.to_csv(info_filename, index=False)
    logger.info("CSV exported.")