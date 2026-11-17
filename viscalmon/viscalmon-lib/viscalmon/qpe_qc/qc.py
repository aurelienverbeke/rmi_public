import datetime
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.signal as scsg

from viscalmon.general.cached_interpolator import CachedInterpolator
from viscalmon.general.exceptions import (
    AccumulationTimesNotDivisible,
    DifferentAccumulationTimesException,
    NotEnoughPeriodsAvailableException,
    RainGaugeAccTimeGreaterThanRadarAccTimeException,
)
from viscalmon.general.io.radar import open_hdf
from viscalmon.general.io.rain_gauge import get_rain_gauges_data
from viscalmon.general.io.utils import (
    acc_time_from_product_name,
    scale_from_product_name,
    software_from_product_name,
)
from viscalmon.qpe_qc.constants import AVAILABLE_RADARS
from viscalmon.qpe_qc.stats import StatsType, stats
from viscalmon.qpe_qc.utils import get_and_filter_files_names

MARGIN = np.sqrt(2)*1.05
CHUNKS_MAX_SIZE = 100
OVERSAMPLING_RATE = 100
MAX_SHIFT_N_BASE_TIME = 3
PEAK_RELATIVE_HEIGHT = 0.5
PEAK_RELATIVE_PROMINENCE = 0.5





# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)





def compare_r_r(end_timestamp : datetime.datetime, duration : datetime.timedelta,
                     min_availability : float, min_precip_rates : list[float],
                     product_type_1 : str, product_type_2 : str,
                     radar_1 : str|None = None, radar_2 : str|None = None) \
                -> dict[float, StatsType]:
    """
        Compare two products and computes statistics on a specific period.

        Parameters
        ----------
        timestamp : datetime.datetime
            End of the period.
        
        duration : datetime.timedelta
            Duration of the period
        
        min_availability : float
            Minimum availability of the data.
            Counted as ratio between the number of available products couples
            and the theoretical number of periods in `duration`
            regarding the radar product accumulation time.
        
        min_precip_rates : list of float
            Minimum pricipitation rates, in mm/hr.
            Keeps only couples where at least of one of both value sexceeds those values.
        
        product_type_1 : str
            Name of the first product to compare.
            See `viscalmon.general.io.constants.RADAR_PRODUCTS_TYPES`.
        
        product_type_2 : str
            Name of the second product to compare.
            See `viscalmon.general.io.constants.RADAR_PRODUCTS_TYPES`.

        radar_1 : str, optional
            Name of the associated radar for the first product, if it is a single-radar product.
            See `constants.AVAILABLE_RADARS`.

        radar_2 : str, optional
            Name of the associated radar for the second product, if it is a single-radar product.
            See `constants.AVAILABLE_RADARS`.

        Returns
        -------
        dict(float, viscalmon.qpe_qc.stats.StatsType)
            Dict that associates a a minimum pricipation rate and its statistics:
            See `viscalmon.qpe_qc.stats.stats`.

        Raises
        ------
        DifferentAccumulationTimesException
            If both products are radar observations and don't have the same accumulation time.

        ValueError
            If the associated radar is not specified for a single-radar product or a product type is wrong.

        NotEnoughPeriodsAvailableException
            If `min_availability` cannot be respected.
    """

    ##########
    # Verification of all parameters
    ##########

    acc_time_1 = acc_time_from_product_name(product_type_1)
    acc_time_2 = acc_time_from_product_name(product_type_2)

    if acc_time_1 != acc_time_2:
        raise DifferentAccumulationTimesException()
    
    if scale_from_product_name(product_type_1) == "single" and radar_1 not in AVAILABLE_RADARS \
            or scale_from_product_name(product_type_2) == "single" and radar_2 not in AVAILABLE_RADARS:
        raise ValueError("Wrong radar name.")



    # Add 1 min to avoid getting the first data corresponding to timestamp (timestamp-duration),
    # that won't be used after
    logger.info("Increasing begin timestamp 1 minute to avoid getting the data corresponding to end-duration.")
    begin_timestamp = end_timestamp - duration + datetime.timedelta(minutes=1)
    
    

    ##########
    # Data assimilation
    ##########

    logger.info("Opening radar 1 files.")
    radar_files_1 = get_and_filter_files_names(product_type_1, begin_timestamp, end_timestamp, radar_1)
    radar_data_1 = open_hdf(radar_files_1, software_from_product_name(product_type_1))

    logger.info("Opening radar 2 files.")
    radar_files_2 = get_and_filter_files_names(product_type_2, begin_timestamp, end_timestamp, radar_2)
    radar_data_2 = open_hdf(radar_files_2, software_from_product_name(product_type_2))
    


    ##########
    # Verify if the minimum availability is respected
    ##########
    
    logger.info("Verifying minimum availability.")
    
    if acc_time_2 == datetime.timedelta():
        nb_expected_periods = duration // datetime.timedelta(minutes=5)
    else:
        nb_expected_periods = duration // acc_time_2

    # Take intersection of both available radar data periods timestamps
    available_timestamps = set(radar_data_1.keys()) & set(radar_data_2.keys())
    if len(available_timestamps) < nb_expected_periods*min_availability:
        raise NotEnoughPeriodsAvailableException()



    ##########
    # Statistics computation
    ##########

    logger.info("Merging corresponding radar data.")

    interpolator = CachedInterpolator()

    data_1_chunks = []
    data_2_chunks = []

    for timestamp in available_timestamps:
        logger.info(f"Processing timestamp {timestamp}")

        r1 = radar_data_1[timestamp]
        r2 = radar_data_2[timestamp]

        flat_r1_lon = r1.coords["lon"].data.flatten()
        flat_r1_lat = r1.coords["lat"].data.flatten()
        flat_r2_lon = r2.coords["lon"].data.flatten()
        flat_r2_lat = r2.coords["lat"].data.flatten()

        # Get common indexes between both matrixes
        key = (r2.attrs["proj"], flat_r2_lon[0], flat_r2_lat[0], \
                r2.attrs["n_x_pixels"], r2.attrs["n_y_pixels"], r2.attrs["x_pixel_res"], r2.attrs["y_pixel_res"])
        
        if interpolator.exists(*key):
            logger.debug(f"Interpolator key {key} already exists.")
        else:
            logger.debug(f"Adding interpolator key {key}.")
            interpolator.add_interpolation_radar_grid(r2.attrs["proj"], flat_r2_lon, flat_r2_lat, \
                                                    r2.attrs["n_x_pixels"], r2.attrs["n_y_pixels"], \
                                                    r2.attrs["x_pixel_res"], r2.attrs["y_pixel_res"])

        indexes_couples_1, indexes_couples_2 = interpolator.interpolated_indexes( \
                                                key, \
                                                flat_r1_lon, flat_r1_lat, \
                                                np.arcsin(np.max([r1.attrs["x_pixel_res"], r1.attrs["y_pixel_res"], r2.attrs["x_pixel_res"], r2.attrs["y_pixel_res"]])/6371)*MARGIN*180./np.pi)
        
        # Valid couples usable for statistics
        data_1_chunks.append(r1.to_numpy().flatten()[indexes_couples_1])
        data_2_chunks.append(r2.to_numpy().flatten()[indexes_couples_2])
    
    data_1 = np.concatenate(data_1_chunks) if data_1_chunks else np.array([])
    data_2 = np.concatenate(data_2_chunks) if data_2_chunks else np.array([])

    
    
    # Convert minimum precipitayion rates from mm/hr to mm/[accumulation time]
    logger.info("Adapting minimum precipitation rates to accumulation time.")

    if acc_time_1 == datetime.timedelta() or acc_time_1 == datetime.timedelta(hours=1):
        min_precip_values = min_precip_rates
    else:
        min_precip_values = np.array(min_precip_rates) / (datetime.timedelta(hours=1) / acc_time_1)
    
    logger.debug(f"min_precip_rates: {min_precip_rates}")
    logger.debug(f"min_precip_values: {min_precip_values}")
        
    

    logger.info("Computing stats and returning.")
    return dict(zip(min_precip_rates, stats(min_precip_values, "any", data_1, data_2)))





def compare_g_r(timestamp : datetime.datetime, duration : datetime.timedelta,
                    min_availability : float, min_precip_rates : list[float],
                    product_type_g : str, product_type_r : str,
                    radar : str|None = None) \
                -> dict[tuple[int, float, float], dict[float, StatsType]]:
    """
        Compare two products and computes statistics on a specific period.

        Parameters
        ----------
        timestamp : datetime.datetime
            End of the period.
        
        duration : datetime.timedelta
            Duration of the period
        
        min_availability : float
            Minimum availability of the data.
            Counted as ratio between the number of available products couples
            and the theoretical number of periods in `duration`
            regarding the radar product accumulation time.
        
        min_precip_rates : list of float
            Minimum pricipitation rates, in mm/hr.
            Keeps only couples where the rain gauge value exceeds those values.
        
        product_type_g : str
            Name of the first product to compare.
            See `viscalmon.general.io.constants.GAUGE_PRODUCTS_TYPES`.
        
        product_type_r : str
            Name of the second product to compare.
            See `viscalmon.general.io.constants.RADAR_PRODUCTS_TYPES`.

        radar : str, optional
            Name of the associated radar for the second product, if it is a single-radar product.
            See `constants.AVAILABLE_RADARS`.

        Returns
        -------
        dict(tuple, dict(float, viscalmon.qpe_qc.stats.StatsType))
            Dict that associates a gauge (id, longitude, latitude), a minimum pricipation rate and its statistics:
            See `viscalmon.qpe_qc.stats.stats`.

        Raises
        ------
        AccumulationTimesNotDivisible
            If both accumulation times are not divisible.

        RainGaugeAccTimeGreaterThanRadarAccTimeException
            If the rain gauge accumulation time is greater than the radar one.

        ValueError
            If the associated radar is not specified for a single-radar product or a product type is wrong.
        
        NotEnoughPeriodsAvailableException
            If `min_availability` cannot be respected.
    """

    ##########
    # Verification of all parameters
    ##########

    acc_time_g = acc_time_from_product_name(product_type_g)
    acc_time_r = acc_time_from_product_name(product_type_r)

    if acc_time_g > acc_time_r:
        raise RainGaugeAccTimeGreaterThanRadarAccTimeException()
    
    if acc_time_r%acc_time_g!=datetime.timedelta():
        raise AccumulationTimesNotDivisible()
    
    if scale_from_product_name(product_type_r) == "single" and radar not in AVAILABLE_RADARS:
        raise ValueError("Wrong radar name.")



    # Add 1 min to avoid getting the first data corresponding to timestamp (timestamp-duration),
    # that won't be used after
    logger.info("Increasing begin timestamp 1 minute to avoid getting the data corresponding to end-duration.")
    begin_timestamp = timestamp - duration + datetime.timedelta(minutes=1)
    
    

    ##########
    # Gauges data assimilation
    ##########
    
    logger.info("Getting gauges data.")
    
    gauges_data = get_rain_gauges_data(product_type_g, begin_timestamp, timestamp, \
                        os.environ["ORACLE_USER"], os.environ["ORACLE_PASSWORD"], \
                        os.environ["ORACLE_HOST"], os.environ["ORACLE_PORT"], os.environ["ORACLE_SERVICE"])
    
    # Remove non-validated or non-corrected data
    gauges_data = gauges_data[gauges_data["validated"] | gauges_data["corrected"]]
    
    # Normally, we shouldn't have any problems of different locations
    # for a single gauge thanks to the to sql query

    acc_time_ratio = acc_time_r // acc_time_g

    # Group by gauge and accumulation time of the radar data
    # Accumulate rain gauges data if necessary
    if acc_time_ratio != 1:
        logger.info("Grouping gauges data to match radar accumulation time.")

        # Here normally acc_time_g<acc_time_r and acc_time_r%acc_time_g==0

        acc_time_pd = pd.Timedelta(acc_time_r)
        ref = pd.Timestamp(timestamp)  # anchor buckets to the requested window, not to midnight

        # Number of whole acc_time_r periods since ref, then ceil -> bucket end
        elapsed = ref - gauges_data["timestamp"]
        periods = elapsed // acc_time_pd
        gauges_data["bucket"] = ref - periods * acc_time_pd
        
        gauges_data = gauges_data.groupby(["station_id", "bucket"]).agg(
                            lon=("lon", "first"),
                            lat=("lat", "first"),
                            quantity=("quantity", "sum"),
                            validated=("validated", "all"),
                            corrected=("corrected", "any"),
                            count=("timestamp", "count")
                        ).reset_index()

        # For consistency
        gauges_data.rename(columns={"bucket" : "timestamp"}, inplace=True)
    
    else:
        logger.info("No need for data grouping.")

        # For consistency
        gauges_data["count"] = 1

    # Verify enough values
    gauges_data = gauges_data[gauges_data["count"] == acc_time_ratio]



    ##########
    # Radar data assimilation
    #
    # Here we we'll probably open a lot of files, so we do it by chunks of size max. CHUNKS_MAX_SIZE,
    # hence avoidid filling the memory
    # 
    # We do it asynchronously, retrieving the next chunk while matching values from radar and rain gauge
    # Since opening the file is slower than calculations, the run time corresponds to open_hdf() time
    ##########

    logger.info("Opening radar files and adding corresponding pixel values to the rain gauges dataframe.")

    # Prepare dataframe
    gauges_data["radar_quantity"] = np.nan

    radar_files = get_and_filter_files_names(product_type_r, begin_timestamp, timestamp, radar)
    software = software_from_product_name(product_type_r)
    chunks = [ radar_files[i : i+CHUNKS_MAX_SIZE] for i in range(0, len(radar_files), CHUNKS_MAX_SIZE) ]

    interpolator = CachedInterpolator()
    executor = ThreadPoolExecutor(max_workers=1)

    # Group gauges measurements by timestamp for accelerating the loop after
    gauges_by_timestamp = dict(tuple(gauges_data.groupby("timestamp")))

    result_indices = []
    result_values = []

    # Open first chunk
    future = executor.submit(open_hdf, chunks[0], software)

    logger.debug(f"Number of chunks: {len(chunks)}")
    for i in range(len(chunks)):
        logger.debug(f"Chunk {i}")

        # Wait for the chunk to be opened
        radar_data = future.result()

        # If exists, open the next chunck
        if i + 1 < len(chunks):
            future = executor.submit(open_hdf, chunks[i + 1], software)

        for ts, r in radar_data.items():
            logger.info(f"Processing timestamp {ts}")

            # Get all lats and lons
            gauges_for_timestamp = gauges_by_timestamp.get(ts)
            if gauges_for_timestamp is None or gauges_for_timestamp.empty:
                # No rain gauge for this timestamp
                continue
            gauges_lons = gauges_for_timestamp["lon"].to_numpy()
            gauges_lats = gauges_for_timestamp["lat"].to_numpy()

            flat_r_lon = r.coords["lon"].data.flatten()
            flat_r_lat = r.coords["lat"].data.flatten()

            # Get common indexes between both matrixes
            key = (r.attrs["proj"], flat_r_lon[0], flat_r_lat[0], \
                    r.attrs["n_x_pixels"], r.attrs["n_y_pixels"], r.attrs["x_pixel_res"], r.attrs["y_pixel_res"])
            
            if interpolator.exists(*key):
                logger.debug(f"Interpolator key {key} already exists.")
            else:
                logger.debug(f"Adding interpolator key {key}.")
                interpolator.add_interpolation_radar_grid(r.attrs["proj"], flat_r_lon, flat_r_lat, \
                                                        r.attrs["n_x_pixels"], r.attrs["n_y_pixels"], \
                                                        r.attrs["x_pixel_res"], r.attrs["y_pixel_res"])

            indexes_couples_g, indexes_couples_r = interpolator.interpolated_indexes( \
                                                        key, \
                                                        gauges_lons, gauges_lats, \
                                                        np.arcsin(np.max([r.attrs["x_pixel_res"], r.attrs["y_pixel_res"]])/6371)*MARGIN*180./np.pi)

            # Get and store :
            # - Radar values
            # - Corresponding indexes in the gauges dataframe
            matched_original_index = gauges_for_timestamp.index[indexes_couples_g]
            matched_values = r.to_numpy().flatten()[indexes_couples_r]

            result_indices.append(matched_original_index)
            result_values.append(matched_values)

    executor.shutdown()
    
    # Put all radar values in the dataframe
    if result_indices:
        all_indices = np.concatenate([idx.to_numpy() for idx in result_indices])
        all_values = np.concatenate(result_values)
        all_values[np.isnan(all_values)] = 0.0 # Sometimes 0mm is set as nan
        gauges_data.loc[all_indices, "radar_quantity"] = all_values



    ##########
    # Verify if the minimum availability is respected
    ##########

    logger.info("Verifying minimum availability.")
    
    nb_expected_periods = duration // acc_time_r
    logger.debug(nb_expected_periods)

    # Remove each row where we don't have gauge value or radar value
    logger.debug(gauges_data)
    both_quantities_available = ~gauges_data["quantity"].isna() & ~gauges_data["radar_quantity"].isna()
    gauges_data = gauges_data[both_quantities_available]

    # Remove station if the minimum availability isn't respected
    counts = gauges_data.groupby("station_id").agg(count=("timestamp", "count"))["count"]
    valid_stations_ids = counts[counts >= nb_expected_periods*min_availability].index.to_numpy()
    gauges_data = gauges_data[gauges_data["station_id"].isin(valid_stations_ids)]
    
    if gauges_data.empty:
        raise NotEnoughPeriodsAvailableException()



    ##########
    # Statistics computation
    ##########

    stats_by_gauge = {}

    # Convert from mm/hr to mm/[accumulation time]
    logger.info("Adapting minimum precipitation rates to accumulation time.")
    min_precip_values = np.array(min_precip_rates) / (datetime.timedelta(hours=1) / acc_time_r)
    logger.debug(f"min_precip_rates: {min_precip_rates}")
    logger.debug(f"min_precip_values: {min_precip_values}")
    
    logger.info("Computing stats and returning.")
    for station_id, station_data in gauges_data.groupby("station_id"):
        stats_by_gauge[(station_id, station_data["lon"].iat[0], station_data["lat"].iat[0])] \
            = dict(zip(min_precip_rates, stats(min_precip_values, "reference", station_data["quantity"].to_numpy(dtype=np.float32), station_data["radar_quantity"].to_numpy(dtype=np.float32))))

    return stats_by_gauge





def g_r_synchronization(timestamp : datetime.datetime, duration : datetime.timedelta,
                            min_availability : float,
                            product_type_g : str, product_type_r : str,
                            radar : str|None = None) \
                        -> dict[tuple[int, float, float], tuple[int, int|None]]:
    """
        Computes the mean temporal shift between radar estimations and gauges measurements.

        Before computing cross-correlation, the time resolution is systematically multiplied by 100 and the values are timely interpolated.

        The maximum of the cross-correlation can only be found in [center - 3*base time ; center + 3*base time]
        where the base time is the radar accumulation time or the product generation frequency for rainfall rates.

        Parameters
        ----------
        timestamp : datetime.datetime
            End of the period.
        
        duration : datetime.timedelta
            Duration of the period
        
        min_availability : float
            Minimum availability of the data.
            Counted as ratio between the number of available products couples
            and the theoretical number of periods in `duration`
            regarding the radar product accumulation time.
        
        product_type_g : str
            Name of the gauge product to use.
            See `viscalmon.general.io.constants.GAUGE_PRODUCTS_TYPES`.
        
        product_type_r : str
            Name of the radar product to use.
            See `viscalmon.general.io.constants.RADAR_PRODUCTS_TYPES`.

        radar : str, optional
            Name of the associated radar for the radar product, if it is a single-radar product.
            See `constants.AVAILABLE_RADARS`.

        Returns
        -------
        dict((int, float, float), (int, int|None)))
            Dict that associates a gauge (id, longitude, latitude) and :
            - the number of strictly positive gauge measurements
            - the mean temporal shift in seconds, None if it exceeds the [center - 3*base time ; center + 3*base time] range.

        Raises
        ------
        AccumulationTimesNotDivisible
            If both accumulation times are not divisible.

        RainGaugeAccTimeGreaterThanRadarAccTimeException
            If the rain gauge accumulation time is greater than the radar one.

        ValueError
            If the associated radar is not specified for a single-radar product or a product type is wrong.
        
        NotEnoughPeriodsAvailableException
            If `min_availability` cannot be respected.
    """

    ##########
    # Verification of all parameters
    ##########

    acc_time_g = acc_time_from_product_name(product_type_g)
    acc_time_r = acc_time_from_product_name(product_type_r)

    # Correct for rainfall rates
    if acc_time_r == datetime.timedelta():
        acc_time_r = datetime.timedelta(minutes=5)
    
    if acc_time_g > acc_time_r:
        raise RainGaugeAccTimeGreaterThanRadarAccTimeException()
    
    if acc_time_r%acc_time_g!=datetime.timedelta():
        raise AccumulationTimesNotDivisible()
    
    if scale_from_product_name(product_type_r) == "single" and radar not in AVAILABLE_RADARS:
        raise ValueError("Wrong radar name.")



    # Add 1 min to avoid getting the first data corresponding to timestamp (timestamp-duration),
    # that won't be used after
    logger.info("Increasing begin timestamp 1 minute to avoid getting the data corresponding to end-duration.")
    begin_timestamp = timestamp - duration + datetime.timedelta(minutes=1)
    
    

    ##########
    # Gauges data assimilation
    ##########
    
    logger.info("Getting gauges data.")
    
    gauges_data = get_rain_gauges_data(product_type_g, begin_timestamp, timestamp, \
                        os.environ["ORACLE_USER"], os.environ["ORACLE_PASSWORD"], \
                        os.environ["ORACLE_HOST"], int(os.environ["ORACLE_PORT"]), os.environ["ORACLE_SERVICE"])
    
    # Remove non-validated or non-corrected data
    gauges_data = gauges_data[gauges_data["validated"] | gauges_data["corrected"]]
    
    # Normally, we shouldn't have any problems of different locations
    # for a single gauge thanks to the to sql query

    acc_time_ratio = acc_time_r // acc_time_g

    # Group by gauge and accumulation time of the radar data
    # Accumulate rain gauges data if necessary
    if acc_time_ratio != 1:
        logger.info("Grouping gauges data to match radar accumulation time.")

        # Here normally acc_time_g<acc_time_r and acc_time_r%acc_time_g==0

        acc_time_pd = pd.Timedelta(acc_time_r)
        ref = pd.Timestamp(timestamp)  # anchor buckets to the requested window, not to midnight

        # Number of whole acc_time_r periods since ref, then ceil -> bucket end
        elapsed = ref - gauges_data["timestamp"]
        periods = elapsed // acc_time_pd
        gauges_data["bucket"] = ref - periods * acc_time_pd
        
        gauges_data = gauges_data.groupby(["station_id", "bucket"]).agg(
                            lon=("lon", "first"),
                            lat=("lat", "first"),
                            quantity=("quantity", "sum"),
                            validated=("validated", "all"),
                            corrected=("corrected", "any"),
                            count=("timestamp", "count")
                        ).reset_index()

        # For consistency
        gauges_data.rename(columns={"bucket" : "timestamp"}, inplace=True)
    
    else:
        logger.info("No need for data grouping.")

        # For consistency
        gauges_data["count"] = 1

    # Verify enough values
    gauges_data = gauges_data[gauges_data["count"] == acc_time_ratio]



    ##########
    # Radar data assimilation
    #
    # Here we we'll probably open a lot of files, so we do it by chunks of size max. CHUNKS_MAX_SIZE,
    # hence avoidid filling the memory
    # 
    # We do it asynchronously, retrieving the next chunk while matching values from radar and rain gauge
    # Since opening the file is slower than calculations, the run time corresponds to open_hdf() time
    ##########

    logger.info("Opening radar files and adding corresponding pixel values to the rain gauges dataframe.")

    # Prepare dataframe
    gauges_data["radar_quantity"] = np.nan

    radar_files = sorted(get_and_filter_files_names(product_type_r, begin_timestamp, timestamp, radar))
    software = software_from_product_name(product_type_r)
    chunks = [ radar_files[i : i+CHUNKS_MAX_SIZE] for i in range(0, len(radar_files), CHUNKS_MAX_SIZE) ]

    interpolator = CachedInterpolator()
    executor = ThreadPoolExecutor(max_workers=1)

    # Group gauges measurements by timestamp for accelerating the loop after
    gauges_by_timestamp = dict(tuple(gauges_data.groupby("timestamp")))

    result_indices = []
    result_values = []

    # Open first chunk
    future = executor.submit(open_hdf, chunks[0], software)

    logger.debug(f"Number of chunks: {len(chunks)}")
    for i in range(len(chunks)):
        logger.debug(f"Chunk {i}")

        # Wait for the chunk to be opened
        radar_data = future.result()

        # If exists, open the next chunck
        if i + 1 < len(chunks):
            future = executor.submit(open_hdf, chunks[i + 1], software)

        for ts, r in radar_data.items():
            logger.info(f"Processing timestamp {ts}")

            # Get all lats and lons
            gauges_for_timestamp = gauges_by_timestamp.get(ts)
            if gauges_for_timestamp is None or gauges_for_timestamp.empty:
                # No rain gauge for this timestamp
                continue
            gauges_lons = gauges_for_timestamp["lon"].to_numpy()
            gauges_lats = gauges_for_timestamp["lat"].to_numpy()

            flat_r_lon = r.coords["lon"].data.flatten()
            flat_r_lat = r.coords["lat"].data.flatten()

            # Get common indexes between both matrixes
            key = (r.attrs["proj"], flat_r_lon[0], flat_r_lat[0], \
                    r.attrs["n_x_pixels"], r.attrs["n_y_pixels"], r.attrs["x_pixel_res"], r.attrs["y_pixel_res"])
            
            if interpolator.exists(*key):
                logger.debug(f"Interpolator key {key} already exists.")
            else:
                logger.debug(f"Adding interpolator key {key}.")
                interpolator.add_interpolation_radar_grid(r.attrs["proj"], flat_r_lon, flat_r_lat, \
                                                        r.attrs["n_x_pixels"], r.attrs["n_y_pixels"], \
                                                        r.attrs["x_pixel_res"], r.attrs["y_pixel_res"])

            indexes_couples_g, indexes_couples_r = interpolator.interpolated_indexes( \
                                                        key, \
                                                        gauges_lons, gauges_lats, \
                                                        np.arcsin(np.max([r.attrs["x_pixel_res"], r.attrs["y_pixel_res"]])/6371)*MARGIN*180./np.pi)

            # Get and store :
            # - Radar values
            # - Corresponding indexes in the gauges dataframe
            matched_original_index = gauges_for_timestamp.index[indexes_couples_g]
            matched_values = r.to_numpy().flatten()[indexes_couples_r]

            result_indices.append(matched_original_index)
            result_values.append(matched_values)

    executor.shutdown()
    
    # Put all radar values in the dataframe
    if result_indices:
        all_indices = np.concatenate([idx.to_numpy() for idx in result_indices])
        all_values = np.concatenate(result_values)
        all_values[np.isnan(all_values)] = 0.0 # Sometimes 0mm is set as nan
        gauges_data.loc[all_indices, "radar_quantity"] = all_values



    ##########
    # Verify if the minimum availability is respected
    ##########

    logger.info("Verifying minimum availability.")
    
    nb_expected_periods = duration // acc_time_r

    # Remove each row where we don't have gauge value or radar value
    both_quantities_available = ~gauges_data["quantity"].isna() & ~gauges_data["radar_quantity"].isna()
    gauges_data = gauges_data[both_quantities_available]

    # Remove station if the minimum availability isn't respected
    counts = gauges_data.groupby("station_id").agg(count=("timestamp", "count"))["count"]
    valid_stations_ids = counts[counts >= nb_expected_periods*min_availability].index.to_numpy()
    gauges_data = gauges_data[gauges_data["station_id"].isin(valid_stations_ids)]
    
    if gauges_data.empty:
        raise NotEnoughPeriodsAvailableException()



    ##########
    # Statistics computation
    ##########

    logger.info("Computing stats.")
    
    shift_by_gauge = {}

    gauges_data_by_gauge = gauges_data.groupby("station_id")
    for i, (station_id, station_data) in enumerate(gauges_data_by_gauge):
        logger.info(f"Computing stats for station {i}/{gauges_data_by_gauge.ngroups} : {station_id}")

        station_data : pd.DataFrame = station_data.sort_values("timestamp").set_index("timestamp")

        n_g_nonzero = station_data["quantity"][station_data["quantity"]>0.].size

        # Fill with 0. rows if missing timestamps
        full_timestamps = pd.date_range(
            start=timestamp-duration,
            end=timestamp,
            freq=acc_time_r,
            inclusive="right"
        )
        station_data = station_data.reindex(full_timestamps)
        station_data = station_data.fillna(value={"quantity":0., "radar_quantity":0.})

        
        # Oversample with ratio 100
        interpolation_freq = acc_time_r / OVERSAMPLING_RATE
        oversampling_timestamps = pd.date_range(
            start=timestamp-duration,
            end=timestamp,
            freq=interpolation_freq,
            inclusive="right"
        )
        station_data = station_data.reindex(oversampling_timestamps)

        # Interpolate linearly
        
        # To fill the first group of nan with 0 instead of nan
        if station_data["quantity"].isna().iat[0]:
            station_data.loc[station_data.index[0], "quantity"] = 0.
        if station_data["radar_quantity"].isna().iat[0]:
            station_data.loc[station_data.index[0], "radar_quantity"] = 0.
        
        station_data[["quantity", "radar_quantity"]] = station_data[["quantity", "radar_quantity"]].interpolate(method="time")

        correlation = scsg.correlate(station_data["radar_quantity"], station_data["quantity"], mode="full")

        if station_id==685:
            plt.plot(station_data["radar_quantity"])
            plt.plot(station_data["quantity"])
            plt.savefig("graph.png")
            plt.plot(correlation)
            plt.savefig("graph2.png")
        
        # Find argmax in the [center - 3*base time ; center + 3*base time] range
        center = station_data.shape[0]-1
        argmax = np.argmax(correlation)
        min_prominence = PEAK_RELATIVE_PROMINENCE*correlation[argmax]
        peaks, _ = scsg.find_peaks(correlation, height=correlation[argmax]*PEAK_RELATIVE_HEIGHT)
        
        if len(peaks) > 0:
            argmax = peaks[np.argmin(np.abs(peaks - center))]
        
        prominence = scsg.peak_prominences(correlation, [argmax])[0][0]
        max_center_dist_samples = MAX_SHIFT_N_BASE_TIME * OVERSAMPLING_RATE
        if np.abs(argmax - center) <= max_center_dist_samples and prominence >= min_prominence:
            timeshift_seconds = int((argmax-center) * interpolation_freq.total_seconds())
        else:
            timeshift_seconds = None
        
        shift_by_gauge[(station_id, station_data["lon"].dropna().iat[0], station_data["lat"].dropna().iat[0])] \
            = (n_g_nonzero, timeshift_seconds)

    
    
    logger.info("Returning.")
    return shift_by_gauge