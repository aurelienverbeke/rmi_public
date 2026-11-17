import datetime
import logging
import os
import re
from multiprocessing import Pool

import numpy as np
import psycopg
import xarray as xr

from viscalmon.general.utils import (
    apply_none_mask,
    filter_rows_or_cols,
    get_distances_heights,
    pad_matrix_right_nan,
    phidp0_from_phidp_rhohv,
)

RHOHV_THRESHOLD = 0.99
MIN_Z = 10 #need int
MAX_Z = 30 #need int
MIN_H = 1 # in km, from radar
MAX_H = 3 # in km, from sea level
MIN_D = 1 # in km
MAX_D = 50 # in km
N_GATES = 10
SMOOTH_WIDTH = 15 # in deg
MIN_N_POINTS_PER_AZIMUTH = 100

MAX_NB_PROCESSES = 16





# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)





def zdr90(radar : str, date : datetime.date, data : dict[tuple[str, float|int], xr.Dataset], alt : float) -> None:
    """
    Computes Zdr90 for one day.

    Returns nothing. Exports the result in the database

    Parameters
    ----------
    radar : string
        Name of the radar
    date : string
        Day to be computed, format YYYYMMDDD
    data : dict((str, float), xarray.Dataset)
        Data to be used. Must contain Zdr and dBZ (eventually RhoHV) files.
    alt : float
        Altitude of the radar in km.
    """

    logger.info("Starting.")

    n_scans = 0
    all_rhohv_scans_available = True
    zdr_medians = []
    n_points = []

    

    # Compute median zdr in rain for each scan
    for ts, data_by_timestamp in data.items():
        logger.info(f"Processing timestamp {ts}")

        # Skip timestamp if missing Zdr or Z
        if "ZDR" not in data_by_timestamp.data_vars \
                or "dBZ" not in data_by_timestamp.data_vars:
            logger.warning("Missing ZDR or dBZ data. Skipping.")
            continue
        
        z = np.copy(data_by_timestamp.data_vars["dBZ"].values)
        zdr = np.copy(data_by_timestamp.data_vars["ZDR"].values)
        
        bin_res, n_bins \
            = data_by_timestamp.attrs["bin_res"], \
                z.shape[1] \
        
        heights = np.linspace(bin_res/2, (n_bins-1/2)*bin_res, n_bins)
        
        
        
        # Remove no-data points
        mask = np.isnan(z) | np.isnan(zdr)

        # Keep points that are rain (RhoHV >= RHOHV_THRESHOLD, if available)
        if "RhoHV" in data_by_timestamp.data_vars:
            logger.info("Available RhoHV.")
            rhohv = data_by_timestamp.data_vars["RhoHV"].values
            mask = mask | (rhohv<RHOHV_THRESHOLD)
        else:
            logger.info("Missing RhoHV.")
            all_rhohv_scans_available = False

        # Stay in light rain
        mask = mask | (z<MIN_Z) | (z>MAX_Z)

        z, zdr = apply_none_mask([z, zdr], mask)

        

        # Reduce to [min_height ; max_height]
        valid_heights_indices = (MIN_H<=heights) & (heights+alt/1000.<=MAX_H)
        zdr_valid, mask = filter_rows_or_cols([zdr, mask], valid_heights_indices, axis=1, keep=True)


        
        n_points_scan = np.count_nonzero(~mask)
        if n_points_scan > 0:
            zdr_medians.append(np.nanmedian(zdr_valid))
            n_points.append(n_points_scan)
        n_scans += 1
        


    zdr_medians = np.array(zdr_medians)
    n_points = np.array(n_points)
    n_points_total = np.sum(n_points)
    mean_zdr = np.sum(zdr_medians*n_points) / n_points_total



    # Save statistics
    logger.info("Exporting to database.")
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "Zdr90" (radar, date, mean_zdr, n_points, n_scans, available_rhohv)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (radar, date)
                DO UPDATE SET
                    mean_zdr = EXCLUDED.mean_zdr,
                    n_points = EXCLUDED.n_points,
                    n_scans = EXCLUDED.n_scans,
                    available_rhohv = EXCLUDED.available_rhohv
                """,
                (radar, date, mean_zdr if not np.isnan(mean_zdr) else None, n_points_total, n_scans, all_rhohv_scans_available))
        
        conn.commit()





def offsets(radar : str, date : datetime.date, zdr_files : list[str], phidp_files : list[str]) -> None:
    """
    Gets mean Ravis offsets for one day.

    Returns nothing. Exports the result in the database

    Parameters
    ----------
    radar : string
        Name of the radar
    date : string
        Day to be computed, format YYYYMMDDD
    zdr_files : list of str
        List of the rainbow Zdr files.
    phidp_files : list of str
        List of the rainbow PhiDP files.
    """

    logger.info("Starting.")

    # Get offsets from files
    logger.info("Retrieving Zdr offsets.")
    pattern = re.compile(r"<spbzdroffpw>(.*?)</spbzdroffpw>")
    offsets_zdr = []
    for file in zdr_files:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    offsets_zdr.append([ float(offset) for offset in match.group(1).split(" ") ])
    offsets_zdr = np.array(offsets_zdr)
    offsets_zdr, = pad_matrix_right_nan([offsets_zdr], 4-offsets_zdr.shape[1])
    
    logger.info("Retrieving PhiDP offsets.")
    pattern = re.compile(r"<spbphidpoffpw>(.*?)</spbphidpoffpw>")
    offsets_phidp = []
    for file in phidp_files:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    offsets_phidp.append([ float(offset) for offset in match.group(1).split(" ") ])
    offsets_phidp = np.array(offsets_phidp)
    offsets_phidp, = pad_matrix_right_nan([offsets_phidp], 4-offsets_phidp.shape[1])



    # Take mean if difference doesn't exceeds :
    # 0.1dB for Zdr
    # 5deg for PhiDP
    logger.info("Computing means.")

    offsets_zdr_mean : list[np.floating | None] = [None] * 4
    offsets_phidp_mean : list[np.floating | None] = [None] * 4

    for i_pw in range(4):
        offsets_zdr_diff = np.nanmax(offsets_zdr[:,i_pw]) - np.nanmin(offsets_zdr[:,i_pw])
        if offsets_zdr_diff <= 0.1:
            offsets_zdr_mean[i_pw] = np.nanmean(offsets_zdr[:,i_pw])
        offsets_phidp_diff = np.nanmax(offsets_phidp[:,i_pw]) - np.nanmin(offsets_phidp[:,i_pw])
        if offsets_phidp_diff <= 5:
            offsets_phidp_mean[i_pw] = np.nanmean(offsets_phidp[:,i_pw])
            
            

    # Save statistics
    logger.info("Exporting to database.")
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                    INSERT INTO "RavisOffset" (
                        radar, date,
                        zdr_0, zdr_1, zdr_2, zdr_3,
                        phidp_0, phidp_1, phidp_2, phidp_3
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (radar, date)
                    DO UPDATE SET
                        zdr_0   = EXCLUDED.zdr_0,
                        zdr_1   = EXCLUDED.zdr_1,
                        zdr_2   = EXCLUDED.zdr_2,
                        zdr_3   = EXCLUDED.zdr_3,
                        phidp_0 = EXCLUDED.phidp_0,
                        phidp_1 = EXCLUDED.phidp_1,
                        phidp_2 = EXCLUDED.phidp_2,
                        phidp_3 = EXCLUDED.phidp_3
                """,
                (radar, date, *offsets_zdr_mean, *offsets_phidp_mean))
        
        conn.commit()





def phidp0(radar : str, date : datetime.date, data : dict[tuple[str, float|int], xr.Dataset]) -> None:
    """
    Computes PhiDP0 for one day.

    Returns nothing. Exports the result in database

    Parameters
    ----------
    radar : string
        Name of the radar
    date : string
        Day to be computed, format YYYYMMDDD
    data : dict((str, float), xarray.Dataset)
        Data to be used. Must contain uPhiDP and RhoHV files.
    """

    logger.info("Starting.")

    # Compute initial phidp per azimuth per scan
    initial_phidps_sin = []
    initial_phidps_cos = []
    for ts, data_by_timestamp_elevation in data.items():
        logger.info(f"Processing timestamp {ts}")
        
        # Skip date if missing PhiDP or RhoHV
        if "uPhiDP" not in data_by_timestamp_elevation.data_vars or "RhoHV" not in data_by_timestamp_elevation.data_vars:
            logger.warning("Missing uPhiDP or RhoHV data. Skipping.")
            continue
        
        phidp = np.copy(data_by_timestamp_elevation.data_vars["uPhiDP"].values)
        rhohv = np.copy(data_by_timestamp_elevation.data_vars["RhoHV"].values)

        # Remove no-data points
        mask = np.isnan(phidp) | np.isnan(rhohv)

        # Keep points that are rain (RhoHV >= RHOHV_THRESHOLD)
        mask = mask | (rhohv<RHOHV_THRESHOLD)

        phidp, = apply_none_mask([phidp], mask)

        # Select first 10 valid gates for each azimuth and compute mean phidp
        scan_initial_phidps_sin = np.full(phidp.shape[0], np.nan)
        scan_initial_phidps_cos = np.full(phidp.shape[0], np.nan)
        mask = ~mask
        for i in range(phidp.shape[0]):
            # Select only non-nan values
            valid_values = phidp[i, mask[i]]
            if valid_values.size >= N_GATES:
                #slower
                #scan_initial_phidps[i] = scst.circmean(valid_values[:N_GATES]*np.pi/180.)*180./np.pi
                rad = valid_values[:N_GATES]*np.pi/180.
                scan_initial_phidps_sin[i] = np.mean(np.sin(rad))
                scan_initial_phidps_cos[i] = np.mean(np.cos(rad))
        
        initial_phidps_sin.append(scan_initial_phidps_sin)
        initial_phidps_cos.append(scan_initial_phidps_cos)
            
    initial_phidps_sin = np.vstack(initial_phidps_sin)
    initial_phidps_cos = np.vstack(initial_phidps_cos)



    # Number of used scans for each azimut
    # Can be computed on sin matrix or cos matrix
    number_used_scans = np.count_nonzero(~np.isnan(initial_phidps_sin), axis=0)

    # Concatenate all elevations with mean
    initial_phidps_sin = np.nanmean(initial_phidps_sin, axis=0)
    initial_phidps_cos = np.nanmean(initial_phidps_cos, axis=0)



    # Smooth with 15deg window median
    initial_phidps_smoothed_sin = np.empty_like(initial_phidps_sin)
    initial_phidps_smoothed_cos = np.empty_like(initial_phidps_cos)
    for azimuth in range(len(initial_phidps_sin)):
        sin_around = np.take(initial_phidps_sin, range(int(azimuth-SMOOTH_WIDTH/2), int(azimuth+SMOOTH_WIDTH/2+1)), mode="wrap")
        cos_around = np.take(initial_phidps_cos, range(int(azimuth-SMOOTH_WIDTH/2), int(azimuth+SMOOTH_WIDTH/2+1)), mode="wrap")
        # flagged as invalid if >50% invalid angles in median
        if np.count_nonzero(np.isnan(sin_around)) < SMOOTH_WIDTH/2:
            initial_phidps_smoothed_sin[azimuth] = np.nanmedian(sin_around)
            initial_phidps_smoothed_cos[azimuth] = np.nanmedian(cos_around)
        else:
            initial_phidps_smoothed_sin[azimuth] = np.nan
            initial_phidps_smoothed_cos[azimuth] = np.nan



    """
    # Interpolate holes with width<30deg
    initial_phidps_smoothed_interp = np.copy(initial_phidps_smoothed)

    # case of index 0 which is after index 359
    azimuth = 0
    while np.isnan(initial_phidps_smoothed_interp[azimuth]) and np.isnan(initial_phidps_smoothed_interp[azimuth-1]):
        azimuth -= 1

    max_index = azimuth + len(initial_phidps_smoothed_interp) - 1
    while azimuth < max_index:
        if not np.isnan(initial_phidps_smoothed_interp[azimuth]):
            azimuth += 1
            continue

        slice_length = 1
        while np.isnan(initial_phidps_smoothed_interp[azimuth+slice_length]):
            slice_length += 1

        if slice_length <= 29:
            start_angle = initial_phidps_smoothed_interp[azimuth-1]
            end_angle = initial_phidps_smoothed_interp[(azimuth+slice_length) % 360]
            
            if abs(end_angle-start_angle) > 180.:
                # around 0deg
                if end_angle >= start_angle:
                    end_angle -= 360.
                else:
                    start_angle -= 360.
            
            interpolated_angles = np.linspace(start_angle, end_angle, slice_length+2) % 360

            np.put(initial_phidps_smoothed_interp, range(azimuth-1, azimuth+slice_length+1), interpolated_angles, mode="wrap")

        # jump to end of nan range
        azimuth += slice_length + 1
    """



    # PhiDP0 final daily offset
    # Weighted mean along azimuths
    total_weights = np.sum(number_used_scans)

    cos_mean = np.nansum(initial_phidps_smoothed_cos*number_used_scans) / total_weights
    sin_mean = np.nansum(initial_phidps_smoothed_sin*number_used_scans) / total_weights

    phidp0 = np.arctan2(sin_mean, cos_mean)*180./np.pi
    
    # arctan2 gives angles between -180deg and 180deg
    if phidp0 < 0:
        phidp0 += 360.



    # Save statistics
    logger.info("Exporting to database.")
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "Phidp0" (radar, date, phidp0, n_gates_ranges)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (radar, date)
                DO UPDATE SET
                    phidp0 = EXCLUDED.phidp0,
                    n_gates_ranges = EXCLUDED.n_gates_ranges
                """,
                (radar, date, phidp0 if not np.isnan(phidp0) else None, total_weights))
        
        conn.commit()





def zdr_rain(radar : str, date : datetime.date, data : dict[tuple[str, float|int], xr.Dataset], alt : float) -> None:
    """
    Computes Zdr_rain for one day.

    Returns nothing. Exports the result in the database

    Parameters
    ----------
    radar : string
        Name of the radar
    date : string
        Day to be computed, format YYYYMMDDD
    data : dict((str, float), xarray.Dataset)
        Data to be used. Must contain Zdr, uPhiDP, RhoHV and dBZ files.
    alt : float
        Altitude of the radar in km.
    """

    logger.info("Starting.")

    medians = []
    number_pixels_used = []

    # Compute median zdr in rain for each azimuth for each scan
    for ts, data_by_timestamp_elevation in data.items():
        logger.info(f"Processing timestamp {ts}")

        # Skip timestamp if missing PhiDP or RhoHV or Zdr or Z
        if "uPhiDP" not in data_by_timestamp_elevation.data_vars \
                or "RhoHV" not in data_by_timestamp_elevation.data_vars \
                or "ZDR" not in data_by_timestamp_elevation.data_vars \
                or "dBZ" not in data_by_timestamp_elevation.data_vars:
            logger.warning("Missing ZDR or dBZ  or uPhiDP or RhoHV data. Skipping.")
            continue
        
        z = np.copy(data_by_timestamp_elevation.data_vars["dBZ"].values)
        zdr = np.copy(data_by_timestamp_elevation.data_vars["ZDR"].values)
        phidp = np.copy(data_by_timestamp_elevation.data_vars["uPhiDP"].values)
        rhohv = np.copy(data_by_timestamp_elevation.data_vars["RhoHV"].values)
        
        bin_res, n_bins, elevation \
            = data_by_timestamp_elevation.attrs["bin_res"], \
                z.shape[1], \
                data_by_timestamp_elevation.attrs["elevation"]
        
        # Remove no-data points
        mask = np.isnan(z) | np.isnan(zdr) | np.isnan(phidp) | np.isnan(rhohv)

        # Keep points that are rain (RhoHV >= RHOHV_THRESHOLD)
        mask = mask | (rhohv<RHOHV_THRESHOLD)

        # Limit Z to [MIN_Z ; MAX_Z]
        mask = mask | (z<MIN_Z) | (z>MAX_Z)

        # Limit to 10°phase shift
        phidp0 = phidp0_from_phidp_rhohv(phidp, rhohv, 15)
        phidps_diff = np.absolute(phidp - phidp0)
        mask = mask | ((phidps_diff > 10) & (phidps_diff<350))

        z, zdr, phidp, rhohv = apply_none_mask([z, zdr, phidp, rhohv], mask)
        
        # Limit distance to antenna to [MIN_D ; MAX_D]
        # And altitude to MAX_H
        distances, heights = get_distances_heights(bin_res, n_bins, elevation, alt)
        valid_ranges = (distances >= MIN_D) & (distances <= MAX_D) & (heights <= MAX_H)

        zdr, = filter_rows_or_cols([zdr], valid_ranges, axis=1, keep=True)

        # Take median for each azimuth
        median = np.nanmedian(zdr, axis=1)
        nb = np.count_nonzero(~np.isnan(zdr), axis=1)

        medians.append(median)
        number_pixels_used.append(nb)
            


    # 1 row = 1 scan
    # 1 column = 1 azimut
    median_zdrs_by_scan = np.vstack(medians)
    n_pixels_by_scan = np.vstack(number_pixels_used)



    # Concatenate all elevations with weighted mean
    n_pixels = np.nansum(n_pixels_by_scan, axis=0)
    mean_zdrs = np.nansum(median_zdrs_by_scan*n_pixels_by_scan, axis=0) / n_pixels



    # Keep azimuths with more than 100 points
    mask = n_pixels < MIN_N_POINTS_PER_AZIMUTH
    mean_zdrs, = apply_none_mask([mean_zdrs], mask)
    n_pixels[mask] = 0



    # Smooth with 15deg window median
    mean_zdrs_smoothed = np.empty_like(mean_zdrs)
    for azimuth in range(len(mean_zdrs)):
        zdrs_around = np.take(mean_zdrs, range(int(azimuth-SMOOTH_WIDTH/2), int(azimuth+SMOOTH_WIDTH/2+1)), mode="wrap")
        # flagged as invalid if >50% invalid zdrs in median
        if np.count_nonzero(np.isnan(zdrs_around)) < SMOOTH_WIDTH/2:
            mean_zdrs_smoothed[azimuth] = np.nanmedian(zdrs_around)
        else:
            mean_zdrs_smoothed[azimuth] = np.nan
            n_pixels[azimuth] = 0



    """
    # Interpolate holes with width<30deg
    mean_zdrs_smoothed_interp = np.copy(mean_zdrs_smoothed)

    # case of index 0 which is after index 359
    azimuth = 0
    while np.isnan(mean_zdrs_smoothed_interp[azimuth]) and np.isnan(mean_zdrs_smoothed_interp[azimuth-1]):
        azimuth -= 1

    max_index = azimuth + len(mean_zdrs_smoothed_interp) - 1
    while azimuth < max_index:
        if not np.isnan(mean_zdrs_smoothed_interp[azimuth]):
            azimuth += 1
            continue

        slice_length = 1
        while np.isnan(mean_zdrs_smoothed_interp[azimuth+slice_length]):
            slice_length += 1

        if slice_length <= 29:
            start_zdr = mean_zdrs_smoothed_interp[azimuth-1]
            end_zdr = mean_zdrs_smoothed_interp[(azimuth+slice_length) % 360]
            
            interpolated_zdrs = np.linspace(start_zdr, end_zdr, slice_length+2) % 360

            np.put(mean_zdrs_smoothed_interp, range(azimuth-1, azimuth+slice_length+1), interpolated_zdrs, mode="wrap")

        # jump to end of nan range
        azimuth += slice_length + 1
    """



    # Zdr final daily offset
    n_points_total = np.nansum(n_pixels)
    zdr_rain = np.nansum(mean_zdrs_smoothed*n_pixels) / n_points_total



    # Save statistics
    logger.info("Exporting to database.")
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "ZdrRain" (radar, date, mean_zdr, n_points)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (radar, date)
                DO UPDATE SET
                    mean_zdr = EXCLUDED.mean_zdr,
                    n_points = EXCLUDED.n_points
                """,
                (radar, date, zdr_rain if not np.isnan(zdr_rain) else None, n_points_total))
        
        conn.commit()





def compute_scan_zdr_rings(scan : xr.Dataset) -> list[np.ndarray]:
    """
    Computes Zdr_rings for one scan.

    Made for parallel use. in `zdr_rings`.

    Parameters
    ----------
    scan : xarray.Dataset
        Scan to be used.
    
    Returns
    -------
    list of numpy.ndarray
        All Zdr values for each ring.
    """

    logger.info(f"Processing timestamp {scan.attrs["timestamp"]}")
    
    if "ZDR" not in scan.data_vars:
        logger.warning("Missing Zdr data. End.")
        return [np.empty((0,))] * 10

    zdrs_by_ring: list[np.ndarray] = []

    distances, _ = get_distances_heights(scan.attrs["bin_res"], scan.data_vars["ZDR"].values.shape[1])
    
    for i in range(10):
        logger.info(f"Processing timestamp {scan.attrs["timestamp"]}, ring {i}")
        distance_filter = (i <= distances) & (distances < i+1)
        ring_zdrs = scan.data_vars["ZDR"].values[:,distance_filter].flatten()
        zdrs_by_ring.append(ring_zdrs[~np.isnan(ring_zdrs)])
    
    return zdrs_by_ring





def zdr_rings(radar : str, date : datetime.date, data : dict[tuple[str, float|int], xr.Dataset]) -> None:
    """
    Computes Zdr_rings for one day.

    Returns nothing. Exports the result in the database

    Parameters
    ----------
    radar : string
        Name of the radar
    date : string
        Day to be computed, format YYYYMMDDD
    data : dict((str, float), xarray.Dataset)
        Data to be used. Must contain Zdr files.
    """

    logger.info("Starting.")

    nb_processes = min(os.process_cpu_count(), MAX_NB_PROCESSES)
    logger.info("Starting processes pool.")
    #multiprocessing.set_start_method('fork')
    with Pool(processes=nb_processes) as pool:
        results = pool.map(compute_scan_zdr_rings, list(data.values()), chunksize=max(len(data)//nb_processes, 1))

    zdrs_by_ring = [ np.concatenate([ result[i] for result in results ]) for i in range(10) ]

    mean_zdr_by_ring = [ np.nanmean(zdrs_ring) for zdrs_ring in zdrs_by_ring ]
    n_points_by_ring = [ len(zdrs_ring) for zdrs_ring in zdrs_by_ring ]

    # NaN to None for database
    mean_zdr_by_ring = [ mean_zdr_ring if not np.isnan(mean_zdr_ring) else None for mean_zdr_ring in mean_zdr_by_ring ]
    n_points_by_ring = [ n_points_ring if not np.isnan(n_points_ring) else None for n_points_ring in n_points_by_ring ]
            
                 
            
    # Save statistics
    logger.info("Exporting to database.")
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "ZdrRings" (
                    radar, date,
                    mean_zdr_1, mean_zdr_2, mean_zdr_3, mean_zdr_4, mean_zdr_5,
                    mean_zdr_6, mean_zdr_7, mean_zdr_8, mean_zdr_9, mean_zdr_10,
                    n_points_1, n_points_2, n_points_3, n_points_4, n_points_5,
                    n_points_6, n_points_7, n_points_8, n_points_9, n_points_10
                )
                VALUES (
                    %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (radar, date)
                DO UPDATE SET
                    mean_zdr_1 = EXCLUDED.mean_zdr_1,
                    mean_zdr_2 = EXCLUDED.mean_zdr_2,
                    mean_zdr_3 = EXCLUDED.mean_zdr_3,
                    mean_zdr_4 = EXCLUDED.mean_zdr_4,
                    mean_zdr_5 = EXCLUDED.mean_zdr_5,
                    mean_zdr_6 = EXCLUDED.mean_zdr_6,
                    mean_zdr_7 = EXCLUDED.mean_zdr_7,
                    mean_zdr_8 = EXCLUDED.mean_zdr_8,
                    mean_zdr_9 = EXCLUDED.mean_zdr_9,
                    mean_zdr_10 = EXCLUDED.mean_zdr_10,
                    n_points_1 = EXCLUDED.n_points_1,
                    n_points_2 = EXCLUDED.n_points_2,
                    n_points_3 = EXCLUDED.n_points_3,
                    n_points_4 = EXCLUDED.n_points_4,
                    n_points_5 = EXCLUDED.n_points_5,
                    n_points_6 = EXCLUDED.n_points_6,
                    n_points_7 = EXCLUDED.n_points_7,
                    n_points_8 = EXCLUDED.n_points_8,
                    n_points_9 = EXCLUDED.n_points_9,
                    n_points_10 = EXCLUDED.n_points_10
                """,
                (radar, date, *mean_zdr_by_ring, *n_points_by_ring))
        
        conn.commit()