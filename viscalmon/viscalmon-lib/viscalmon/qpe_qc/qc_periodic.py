import argparse
import datetime
import logging
import sys
import traceback
from importlib.resources import files

import numpy as np
import pandas as pd
import psycopg
from dateutil import tz

from viscalmon.general.io.constants import GAUGE_PRODUCTS_TYPES, RADAR_PRODUCTS_TYPES
from viscalmon.general.io.utils import (
    acc_time_from_product_name,
    scale_from_product_name,
    software_from_product_name,
)
from viscalmon.qpe_qc.qc import compare_g_r, compare_r_r, g_r_synchronization
from viscalmon.qpe_qc.stats import mean_shift as f_mean_shift
from viscalmon.qpe_qc.stats import mean_stats as f_mean_stats

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)





def compare_r_r_daily(year : int, month : int, day : int,
                        min_availability : float, min_precip_rates : list[float],
                        product_type_1 : str, product_type_2 : str,
                        radar_1 : str|None = None, radar_2 : str|None = None):
    """
        Compares radar data on one day.

        Returns nothing. Exports the result in the database.

        Parameters
        ----------
        year : int
            Year to compute.

        month : int
            Month to compute.
        
        day : int
            Day to compute.
        
        min_availability : float
            See `qc.compare_r_r().`
        
        min_precip_rates : list of float
            See `qc.compare_r_r().`

        product_type_1 : str
            See `qc.compare_r_r().`
        
        product_type_2 : str
            See `qc.compare_r_r().`

        radar_1 : str, optional
            See `qc.compare_r_r().`

        radar_2 : str, optional
            See `qc.compare_r_r().`
    """

    # Ceil-approximate to begin of next day
    end_timestamp = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=1)

    # 1-day accumulations are from 8am l.t. to 8am l.t. (ie 6am or 7am UTC), except for RADQPE2 single radar data
    if acc_time_from_product_name(product_type_1)==datetime.timedelta(days=1) \
            and acc_time_from_product_name(product_type_2)==datetime.timedelta(days=1) \
            and not (scale_from_product_name(product_type_1)=="single" \
                    and scale_from_product_name(product_type_2)=="single" \
                    and software_from_product_name(product_type_1)=="radqpe2" \
                    and software_from_product_name(product_type_1)=="radqpe2"):
        logger.info("Comparing non-single-RADQPE2 data, increasing end timestamp to 8am l.t.")
        utc_zone = tz.gettz("UTC")
        be_zone = tz.gettz("Europe/Brussels")
        end_timestamp = end_timestamp.replace(hour=8, tzinfo=be_zone).astimezone(utc_zone)

    # Cover whole day
    duration = datetime.timedelta(days=1)

    
    
    # Compute statistics
    results = compare_r_r(end_timestamp, duration, min_availability, min_precip_rates, product_type_1, product_type_2, radar_1, radar_2)

    
    
    # Reformat
    stats_array = [
        {
            "date" : datetime.date(year, month, day),
            "product_1" : product_type_1,
            "product_2" : product_type_2,
            "radar_1" : radar_1,
            "radar_2" : radar_2,
            "min_availability" : min_availability,
            "min_precip_rate" : min_precip
        }
        | {
            "var_1" if stat=="var_values" else "var_2" if stat=="var_reference" else stat \
            :\
            value if not np.isnan(value) else None
                for stat, value in stats_min_precip.items()
                if stat not in ["weighted_error", "weighted_bias", "scatter_score"]
        }
            for min_precip, stats_min_precip in results.items()
    ]

    logger.debug(stats_array)



    # Export to database
    logger.info("Exporting to database.")

    query = f"""
        INSERT INTO "Daily_R_R"
            ({", ".join(list(stats_array[0].keys()))})
        VALUES
            ({", ".join([ "%("+key+")s" for key in stats_array[0]])})
        ON CONFLICT ON CONSTRAINT daily_r_r_unique
        DO UPDATE SET
            n_pixels       = EXCLUDED.n_pixels,
            mean_error     = EXCLUDED.mean_error,
            mean_abs_error = EXCLUDED.mean_abs_error,
            rmse           = EXCLUDED.rmse,
            median_error   = EXCLUDED.median_error,
            cov            = EXCLUDED.cov,
            var_1          = EXCLUDED.var_1,
            var_2          = EXCLUDED.var_2,
            corr           = EXCLUDED.corr,
            total_bias     = EXCLUDED.total_bias,
            mean_bias      = EXCLUDED.mean_bias,
            median_bias    = EXCLUDED.median_bias,
            ratio_1_db     = EXCLUDED.ratio_1_db,
            ratio_2_db     = EXCLUDED.ratio_2_db
    """

    logger.debug(query)

    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, stats_array)
        
        conn.commit()





def r_r_monthly_from_daily(year : int, month : int,
                            min_availability : float, min_precip_rates : list[float],
                            product_type_1 : str, product_type_2 : str,
                            radar_1 : str|None = None, radar_2 : str|None = None):
    """
        Compares radar data on one month, retrieving the daily statistics.
        
        Returns nothing. Exports the result in the database.

        Parameters
        ----------
        year : int
            Year to compute.

        month : int
            Month to compute.
        
        min_availability : float
            See `qc.compare_r_r().`
        
        min_precip_rates : list of float
            See `qc.compare_r_r().`

        product_type_1 : str
            See `qc.compare_r_r().`
        
        product_type_2 : str
            See `qc.compare_r_r().`

        radar_1 : str, optional
            See `qc.compare_r_r().`

        radar_2 : str, optional
            See `qc.compare_r_r().`
    """

    for min_precip_rate in min_precip_rates:

        logger.debug(f"Processing minimum precipitation rate {min_precip_rate}")

        with psycopg.connect(row_factory=psycopg.rows.dict_row) as conn, conn.cursor() as cur:
            # Get all daily statistics
            cur.execute(
                """
                SELECT n_pixels, mean_error, mean_abs_error, median_error, rmse, cov, var_1, var_2, corr, total_bias, mean_bias, median_bias, ratio_1_db, ratio_2_db
                FROM
                    "Daily_R_R"
                WHERE
                    date >= %s
                    AND date < %s
                    AND product_1 = %s
                    AND product_2 = %s
                    AND (radar_1 IS NULL OR radar_1 = %s)
                    AND (radar_2 IS NULL OR radar_2 = %s)
                    AND ABS(min_availability-%s) < 0.00001
                    AND ABS(min_precip_rate-%s) < 0.00001
                """,
                [ 
                    datetime.date(year, month, 1),
                    datetime.date(year, month+1, 1) if month < 12 else datetime.date(year+1, 1, 1),
                    product_type_1,
                    product_type_2,
                    radar_1,
                    radar_2,
                    min_availability,
                    min_precip_rate
                ]
            )

            
            
            # Adapt keys and values :
            # None -> np.nan
            # var_1 -> var_values
            # var_2 -> var_reference
            # Add weighted_error, weighted_bias and scatter_score with value np.nan
            rows = [
                {
                    "var_values" if stat=="var_1" else "var_reference" if stat=="var_2" else stat \
                    :\
                    value if value is not None else np.nan
                        for stat, value in row.items()
                }
                | {
                    "weighted_error" : np.nan,
                    "weighted_bias" : np.nan,
                    "scatter_score" : np.nan
                }
                    for row in cur.fetchall()
            ]

            

            # Compute mean stats
            mean_stats = f_mean_stats(rows)

            

            # Reformat
            stats_array = \
                {
                    "month" : datetime.date(year, month, 1),
                    "product_1" : product_type_1,
                    "product_2" : product_type_2,
                    "radar_1" : radar_1,
                    "radar_2" : radar_2,
                    "min_availability" : min_availability,
                    "min_precip_rate" : min_precip_rate
                } \
                | {
                    "var_1" if stat=="var_values" else "var_2" if stat=="var_reference" else stat \
                    :\
                    value if not np.isnan(value) else None
                        for stat, value in mean_stats.items()
                        if stat not in ["weighted_error", "weighted_bias", "scatter_score"]
                }
        
            logger.debug(stats_array)



            # Export to database
            logger.info("Exporting to database.")
        
            query = f"""
                INSERT INTO "Monthly_R_R"
                    ({", ".join(list(stats_array.keys()))})
                VALUES
                    ({", ".join([ "%("+key+")s" for key in stats_array])})
                ON CONFLICT ON CONSTRAINT monthly_r_r_unique
                DO UPDATE SET
                    n_pixels       = EXCLUDED.n_pixels,
                    mean_error     = EXCLUDED.mean_error,
                    mean_abs_error = EXCLUDED.mean_abs_error,
                    rmse           = EXCLUDED.rmse,
                    median_error   = EXCLUDED.median_error,
                    cov            = EXCLUDED.cov,
                    var_1          = EXCLUDED.var_1,
                    var_2          = EXCLUDED.var_2,
                    corr           = EXCLUDED.corr,
                    total_bias     = EXCLUDED.total_bias,
                    mean_bias      = EXCLUDED.mean_bias,
                    median_bias    = EXCLUDED.median_bias,
                    ratio_1_db     = EXCLUDED.ratio_1_db,
                    ratio_2_db     = EXCLUDED.ratio_2_db
            """
        
            logger.debug(query)
        
            cur.execute(query, stats_array)
            conn.commit()







def compare_g_r_daily(year : int, month : int, day : int,
                        min_availability : float, min_precip_rates : list[float],
                        product_type_g : str, product_type_r : str,
                        radar : str|None = None):
    """
        Compares rain gauges and radar data on one day.

        Returns nothing. Exports the result in the database.

        Parameters
        ----------
        year : int
            Year to compute.

        month : int
            Month to compute.
        
        day : int
            Day to compute.
        
        min_availability : float
            See `qc.compare_g_r().`
        
        min_precip_rates : list of float
            See `qc.compare_g_r().`

        product_type_g : str
            See `qc.compare_g_r().`
        
        product_type_r : str
            See `qc.compare_g_r().`

        radar : str, optional
            See `qc.compare_g_r().`
    """

    # Ceil-approximate to begin of next day
    end_timestamp = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=1)

    # 1-day accumulations are from 8am l.t. to 8am l.t. (ie 6am or 7am UTC), except for RADQPE2 single radar data
    if acc_time_from_product_name(product_type_r)==datetime.timedelta(days=1) \
            and not (scale_from_product_name(product_type_r)=="single" \
                    and software_from_product_name(product_type_r)=="radqpe2"):
        logger.info("Comparing non-single-RADQPE2 data, increasing end timestamp to 8am l.t.")
        utc_zone = tz.gettz("UTC")
        be_zone = tz.gettz("Europe/Brussels")
        end_timestamp = end_timestamp.replace(hour=8, tzinfo=be_zone).astimezone(utc_zone)

    # Cover whole day
    duration = datetime.timedelta(days=1)
    

    
    # Compute statistics
    results = compare_g_r(end_timestamp, duration, min_availability, min_precip_rates, product_type_g, product_type_r, radar)

    
    
    # Reformat
    stats_array = [
        {
            "date" : datetime.date(year, month, day),
            "product_g" : product_type_g,
            "product_r" : product_type_r,
            "radar" : radar,
            "station_id" : gauge[0],
            "station_lon" : gauge[1],
            "station_lat" : gauge[2],
            "min_availability" : min_availability,
            "min_precip_rate" : min_precip
        }
        | {
            "var_1" if stat=="var_values" else "var_2" if stat=="var_reference" else stat \
            :\
            value if not np.isnan(value) else None
                for stat, value in stats_gauge_min_precip.items()
        }
            for gauge, stats_gauge in results.items()
            for min_precip, stats_gauge_min_precip in stats_gauge.items()
    ]
    
    logger.debug(stats_array)



    # Export to database

    logger.info("Exporting to database.")

    query = f"""
        INSERT INTO "Daily_G_R"
            ({", ".join(list(stats_array[0].keys()))})
        VALUES
            ({", ".join([ "%("+key+")s" for key in stats_array[0]])})
        ON CONFLICT ON CONSTRAINT daily_g_r_unique
        DO UPDATE SET
            station_lon    = EXCLUDED.station_lon,
            station_lat    = EXCLUDED.station_lat,
            n_pixels       = EXCLUDED.n_pixels,
            mean_error     = EXCLUDED.mean_error,
            mean_abs_error = EXCLUDED.mean_abs_error,
            rmse           = EXCLUDED.rmse,
            median_error   = EXCLUDED.median_error,
            weighted_error = EXCLUDED.weighted_error,
            cov            = EXCLUDED.cov,
            var_1          = EXCLUDED.var_1,
            var_2          = EXCLUDED.var_2,
            corr           = EXCLUDED.corr,
            total_bias     = EXCLUDED.total_bias,
            mean_bias      = EXCLUDED.mean_bias,
            median_bias    = EXCLUDED.median_bias,
            ratio_1_db     = EXCLUDED.ratio_1_db,
            ratio_2_db     = EXCLUDED.ratio_2_db,
            weighted_bias  = EXCLUDED.weighted_bias,
            scatter_score  = EXCLUDED.scatter_score
    """

    logger.debug(query)

    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, stats_array)
        
        conn.commit()





def mean_g_r_daily(year : int, month : int, day : int,
                        min_availability : float, min_precip_rates : list[float],
                        product_type_g : str, product_type_r : str,
                        radar : str|None = None):
    """
        Compares rain gauges and radar data on one day. Averages all gauges statistics.

        Returns nothing. Exports the result in the database.

        Parameters
        ----------
        year : int
            Year to compute.

        month : int
            Month to compute.

        day : int
            Day to compute.
        
        min_availability : float
            See `qc.compare_g_r().`
        
        min_precip_rates : list of float
            See `qc.compare_g_r().`

        product_type_g : str
            See `qc.compare_g_r().`
        
        product_type_r : str
            See `qc.compare_g_r().`

        radar : str, optional
            See `qc.compare_g_r().`
    """

    for min_precip_rate in min_precip_rates:

        logger.debug(f"Processing minimum precipitation rate {min_precip_rate}")

        with psycopg.connect(row_factory=psycopg.rows.dict_row) as conn, conn.cursor() as cur:
            # Get all monthly statistics
            cur.execute(
                """
                SELECT n_pixels, mean_error, mean_abs_error, median_error, weighted_error,
                        rmse, cov, var_1, var_2, corr, total_bias, mean_bias, median_bias,
                        weighted_bias, scatter_score, ratio_1_db, ratio_2_db
                FROM
                    "Daily_G_R"
                WHERE
                    date = %s
                    AND product_r = %s
                    AND product_g = %s
                    AND (radar IS NULL OR radar = %s)
                    AND ABS(min_availability-%s) < 0.00001
                    AND ABS(min_precip_rate-%s) < 0.00001
                """,
                [ 
                    datetime.date(year, month, day),
                    product_type_r,
                    product_type_g,
                    radar,
                    min_availability,
                    min_precip_rate
                ]
            )

            
            
            # Adapt keys and values :
            # None -> np.nan
            # var_1 -> var_values
            # var_2 -> var_reference
            rows = [
                {
                    "var_values" if stat=="var_1" else "var_reference" if stat=="var_2" else stat \
                    :\
                    value if value is not None else np.nan
                        for stat, value in row.items()
                }
                    for row in cur.fetchall()
            ]

            

            # Compute mean stats
            mean_stats = f_mean_stats(rows)

            

            # Reformat
            stats_array = \
                {
                    "date" : datetime.date(year, month, day),
                    "product_r" : product_type_r,
                    "product_g" : product_type_g,
                    "radar" : radar,
                    "min_availability" : min_availability,
                    "min_precip_rate" : min_precip_rate
                } \
                | {
                    "var_1" if stat=="var_values" else "var_2" if stat=="var_reference" else stat \
                    :\
                    value if not np.isnan(value) else None
                        for stat, value in mean_stats.items()
                }
        
            logger.debug(stats_array)



            # Export to database
            logger.info("Exporting to database.")
        
            query = f"""
                INSERT INTO "Daily_Mean_G_R"
                    ({", ".join(list(stats_array.keys()))})
                VALUES
                    ({", ".join([ "%("+key+")s" for key in stats_array])})
                ON CONFLICT ON CONSTRAINT daily_mean_g_r_unique
                DO UPDATE SET
                    n_pixels       = EXCLUDED.n_pixels,
                    mean_error     = EXCLUDED.mean_error,
                    mean_abs_error = EXCLUDED.mean_abs_error,
                    rmse           = EXCLUDED.rmse,
                    median_error   = EXCLUDED.median_error,
                    weighted_error = EXCLUDED.weighted_error,
                    cov            = EXCLUDED.cov,
                    var_1          = EXCLUDED.var_1,
                    var_2          = EXCLUDED.var_2,
                    corr           = EXCLUDED.corr,
                    total_bias     = EXCLUDED.total_bias,
                    mean_bias      = EXCLUDED.mean_bias,
                    median_bias    = EXCLUDED.median_bias,
                    ratio_1_db     = EXCLUDED.ratio_1_db,
                    ratio_2_db     = EXCLUDED.ratio_2_db,
                    weighted_bias  = EXCLUDED.weighted_bias,
                    scatter_score  = EXCLUDED.scatter_score
            """
        
            logger.debug(query)
        
            cur.execute(query, stats_array)
            conn.commit()





def compare_g_r_monthly(year : int, month : int,
                        min_availability : float, min_precip_rates : list[float],
                        product_type_g : str, product_type_r : str,
                        radar : str|None = None):
    """
        Compares rain gauges and radar data on one month.

        Returns nothing. Exports the result in the database.

        Parameters
        ----------
        year : int
            Year to compute.

        month : int
            Month to compute.
        
        min_availability : float
            See `qc.compare_g_r().`
        
        min_precip_rates : list of float
            See `qc.compare_g_r().`

        product_type_g : str
            See `qc.compare_g_r().`
        
        product_type_r : str
            See `qc.compare_g_r().`

        radar : str, optional
            See `qc.compare_g_r().`
    """

    # Ceil-approximate to first day of next month
    if month == 12:
        end_timestamp = datetime.datetime(year+1, 1, 1, tzinfo=datetime.timezone.utc)
    else:
        end_timestamp = datetime.datetime(year, month+1, 1, tzinfo=datetime.timezone.utc)

    # Cover whole month
    duration = end_timestamp - datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)

    # 1-day accumulations are from 8am l.t. to 8am l.t. (ie 6am or 7am UTC), except for RADQPE2 single radar data
    if acc_time_from_product_name(product_type_r)==datetime.timedelta(days=1) \
            and not (scale_from_product_name(product_type_r)=="single" \
                    and software_from_product_name(product_type_r)=="radqpe2"):
        logger.info("Comparing non-single-RADQPE2 data, increasing end timestamp to 8am l.t.")
        utc_zone = tz.gettz("UTC")
        be_zone = tz.gettz("Europe/Brussels")
        end_timestamp = end_timestamp.replace(hour=8, tzinfo=be_zone).astimezone(utc_zone)
    

    
    # Compute statistics
    results = compare_g_r(end_timestamp, duration, min_availability, min_precip_rates, product_type_g, product_type_r, radar)

    
    
    # Reformat
    stats_array = [
        {
            "month" : datetime.date(year, month, 1),
            "product_g" : product_type_g,
            "product_r" : product_type_r,
            "radar" : radar,
            "station_id" : gauge[0],
            "station_lon" : gauge[1],
            "station_lat" : gauge[2],
            "min_availability" : min_availability,
            "min_precip_rate" : min_precip
        }
        | {
            "var_1" if stat=="var_values" else "var_2" if stat=="var_reference" else stat \
            :\
            value if not np.isnan(value) else None
                for stat, value in stats_gauge_min_precip.items()
        }
            for gauge, stats_gauge in results.items()
            for min_precip, stats_gauge_min_precip in stats_gauge.items()
    ]
        
    logger.debug(stats_array)



    # Export to database
    
    logger.info("Exporting to database.")

    query = f"""
        INSERT INTO "Monthly_G_R"
            ({", ".join(list(stats_array[0].keys()))})
        VALUES
            ({", ".join([ "%("+key+")s" for key in stats_array[0]])})
        ON CONFLICT ON CONSTRAINT monthly_gr_unique
        DO UPDATE SET
            station_lon    = EXCLUDED.station_lon,
            station_lat    = EXCLUDED.station_lat,
            n_pixels       = EXCLUDED.n_pixels,
            mean_error     = EXCLUDED.mean_error,
            mean_abs_error = EXCLUDED.mean_abs_error,
            rmse           = EXCLUDED.rmse,
            median_error   = EXCLUDED.median_error,
            weighted_error = EXCLUDED.weighted_error,
            cov            = EXCLUDED.cov,
            var_1          = EXCLUDED.var_1,
            var_2          = EXCLUDED.var_2,
            corr           = EXCLUDED.corr,
            total_bias     = EXCLUDED.total_bias,
            mean_bias      = EXCLUDED.mean_bias,
            median_bias    = EXCLUDED.median_bias,
            ratio_1_db     = EXCLUDED.ratio_1_db,
            ratio_2_db     = EXCLUDED.ratio_2_db,
            weighted_bias  = EXCLUDED.weighted_bias,
            scatter_score  = EXCLUDED.scatter_score
    """

    logger.debug(query)

    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, stats_array)
        
        conn.commit()





def mean_g_r_monthly(year : int, month : int,
                        min_availability : float, min_precip_rates : list[float],
                        product_type_g : str, product_type_r : str,
                        radar : str|None = None):
    """
        Compares rain gauges and radar data on one month. Averages all gauges statistics.

        Returns nothing. Exports the result in the database.

        Parameters
        ----------
        year : int
            Year to compute.

        month : int
            Month to compute.
        
        min_availability : float
            See `qc.compare_g_r().`
        
        min_precip_rates : list of float
            See `qc.compare_g_r().`

        product_type_g : str
            See `qc.compare_g_r().`
        
        product_type_r : str
            See `qc.compare_g_r().`

        radar : str, optional
            See `qc.compare_g_r().`
    """

    for min_precip_rate in min_precip_rates:

        logger.debug(f"Processing minimum precipitation rate {min_precip_rate}")

        with psycopg.connect(row_factory=psycopg.rows.dict_row) as conn, conn.cursor() as cur:
                # Get all monthly statistics
                cur.execute(
                    """
                    SELECT n_pixels, mean_error, mean_abs_error, median_error, weighted_error,
                            rmse, cov, var_1, var_2, corr, total_bias, mean_bias, median_bias,
                            weighted_bias, scatter_score, ratio_1_db, ratio_2_db
                    FROM
                        "Monthly_G_R"
                    WHERE
                        month = %s
                        AND product_r = %s
                        AND product_g = %s
                        AND (radar IS NULL OR radar = %s)
                        AND ABS(min_availability-%s) < 0.00001
                        AND ABS(min_precip_rate-%s) < 0.00001
                    """,
                    [ 
                        datetime.date(year, month, 1),
                        product_type_r,
                        product_type_g,
                        radar,
                        min_availability,
                        min_precip_rate
                    ]
                )

                
                
                # Adapt keys and values :
                # None -> np.nan
                # var_1 -> var_values
                # var_2 -> var_reference
                rows = [
                    {
                        "var_values" if stat=="var_1" else "var_reference" if stat=="var_2" else stat \
                        :\
                        value if value is not None else np.nan
                            for stat, value in row.items()
                    }
                        for row in cur.fetchall()
                ]

                

                # Compute mean stats
                mean_stats = f_mean_stats(rows)

                

                # Reformat
                stats_array = \
                    {
                        "month" : datetime.date(year, month, 1),
                        "product_r" : product_type_r,
                        "product_g" : product_type_g,
                        "radar" : radar,
                        "min_availability" : min_availability,
                        "min_precip_rate" : min_precip_rate
                    } \
                    | {
                        "var_1" if stat=="var_values" else "var_2" if stat=="var_reference" else stat \
                        :\
                        value if not np.isnan(value) else None
                            for stat, value in mean_stats.items()
                    }
            
                logger.debug(stats_array)



                # Export to database
                logger.info("Exporting to database.")
            
                query = f"""
                    INSERT INTO "Monthly_Mean_G_R"
                        ({", ".join(list(stats_array.keys()))})
                    VALUES
                        ({", ".join([ "%("+key+")s" for key in stats_array])})
                    ON CONFLICT ON CONSTRAINT monthly_mean_g_r_unique
                    DO UPDATE SET
                        n_pixels       = EXCLUDED.n_pixels,
                        mean_error     = EXCLUDED.mean_error,
                        mean_abs_error = EXCLUDED.mean_abs_error,
                        rmse           = EXCLUDED.rmse,
                        median_error   = EXCLUDED.median_error,
                        weighted_error = EXCLUDED.weighted_error,
                        cov            = EXCLUDED.cov,
                        var_1          = EXCLUDED.var_1,
                        var_2          = EXCLUDED.var_2,
                        corr           = EXCLUDED.corr,
                        total_bias     = EXCLUDED.total_bias,
                        mean_bias      = EXCLUDED.mean_bias,
                        median_bias    = EXCLUDED.median_bias,
                        ratio_1_db     = EXCLUDED.ratio_1_db,
                        ratio_2_db     = EXCLUDED.ratio_2_db,
                        weighted_bias  = EXCLUDED.weighted_bias,
                        scatter_score  = EXCLUDED.scatter_score
                """
            
                logger.debug(query)
            
                cur.execute(query, stats_array)
                conn.commit()





def g_r_synchronization_daily(year : int, month : int, day : int,
                        min_availability : float,
                        product_type_g : str, product_type_r : str,
                        radar : str|None = None):
    """
        Compares rain gauges and radar data on one month.

        Returns nothing. Exports the result in the database.

        Parameters
        ----------
        year : int
            Year to compute.

        month : int
            Month to compute.
        
        day : int
            Day to compute.
        
        min_availability : float
            See `qc.g_r_synchronization().`

        product_type_g : str
            See `qc.g_r_synchronization().`
        
        product_type_r : str
            See `qc.g_r_synchronization().`

        radar : str, optional
            See `qc.g_r_synchronization().`
    """

    # Ceil-approximate to begin of next day
    end_timestamp = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=1)

    # 1-day accumulations are from 8am l.t. to 8am l.t. (ie 6am or 7am UTC), except for RADQPE2 single radar data
    if product_type_g=="obs_1d" \
            and not (acc_time_from_product_name(product_type_r)==datetime.timedelta(days=1) \
                    and scale_from_product_name(product_type_r)=="single" \
                    and software_from_product_name(product_type_r)=="radqpe2"):
        logger.info("Comparing non-single-RADQPE2 data, increasing end timestamp to 8am l.t.")
        utc_zone = tz.gettz("UTC")
        be_zone = tz.gettz("Europe/Brussels")
        end_timestamp = end_timestamp.replace(hour=8, tzinfo=be_zone).astimezone(utc_zone)

    # Cover whole day
    duration = datetime.timedelta(days=1)
    

    
    # Compute statistics
    results = g_r_synchronization(end_timestamp, duration, min_availability, product_type_g, product_type_r, radar)

    
    
    # Reformat
    stats_array = [
        [datetime.date(year, month, day), product_type_g, product_type_r, *gauge, radar, min_availability, n_g_nonzero, shift ]
        for gauge, (n_g_nonzero, shift) in results.items()
    ]

    logger.debug(stats_array)



    # Export to database

    logger.info("Exporting to database.")

    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO "Daily_Shift" (
                    date,
                    product_g,
                    product_r,
                    station_id,
                    station_lon,
                    station_lat,
                    radar,
                    min_availability,
                    n_g_nonzero,
                    shift
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT ON CONSTRAINT daily_shift_unique
                DO UPDATE SET
                    station_lon    = EXCLUDED.station_lon,
                    station_lat    = EXCLUDED.station_lat,
                    n_g_nonzero    = EXCLUDED.n_g_nonzero,
                    shift          = EXCLUDED.shift
                """, stats_array)
        
        conn.commit()





def g_r_synchronization_daily_mean(year : int, month : int, day : int,
                        min_availability : float,
                        product_types_g : list[str], product_type_r : str,
                        radar : str|None = None):
    """
        Compares rain gauges and radar data on one month.

        Returns nothing. Exports the result in the database.

        Parameters
        ----------
        year : int
            Year to compute.

        month : int
            Month to compute.
        
        day : int
            Day to compute.
        
        min_availability : float
            See `qc.g_r_synchronization().`

        product_type_g : str
            See `qc.g_r_synchronization().`
        
        product_type_r : str
            See `qc.g_r_synchronization().`

        radar : str, optional
            See `qc.g_r_synchronization().`
    """

    # Get all daily statistics
    with psycopg.connect(row_factory=psycopg.rows.dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT station_lon, station_lat, shift, n_g_nonzero
            FROM
                "Daily_Shift"
            WHERE
                date = %s
                AND product_r = %s
                AND product_g = ANY(%s)
                AND (radar IS NULL OR radar = %s)
                AND ABS(min_availability-%s) < 0.00001
            """,
            [ 
                datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc),
                product_type_r,
                product_types_g,
                radar,
                min_availability
            ]
        )



        rows = cur.fetchall()
        shifts = np.array([ row["shift"] if row["shift"] is not None else np.nan for row in rows ])
        n_g_nonzeros = np.array([ row["n_g_nonzero"] for row in rows ])



        if scale_from_product_name(product_type_r) == "single":
            lons = np.array([ row["station_lon"] for row in rows ])
            lats = np.array([ row["station_lat"] for row in rows ])

            # Get radar pos
            csv_path = files("viscalmon.general").joinpath("radar_pos.csv")
            with csv_path.open("r") as f:
                pos_df = pd.read_csv(f)
            pos = pos_df[pos_df["radar"]==radar].iloc[0]
            radar_lon = pos["lon"]
            radar_lat = pos["lat"]

            # Compute mean stats
            mean_shift, n_g_nonzero = f_mean_shift(shifts, n_g_nonzeros, radar_lon, radar_lat, lons, lats)
        
        else:
            # Compute mean stats
            mean_shift, n_g_nonzero = f_mean_shift(shifts, n_g_nonzeros)

        

        # Reformat
        row = [
            datetime.date(year, month, day),
            product_type_r,
            ",".join(product_types_g),
            radar,
            min_availability,
            n_g_nonzero,
            mean_shift
        ]

        logger.debug(row)



        # Export to database
        logger.info("Exporting to database.")
    
        cur.execute("""
            INSERT INTO "Daily_Mean_Shift" (
                date,
                product_r,
                products_g,
                radar,
                min_availability,
                n_g_nonzero,
                shift
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT ON CONSTRAINT daily_mean_shift_unique
            DO UPDATE SET
                n_g_nonzero    = EXCLUDED.n_g_nonzero,
                shift          = EXCLUDED.shift
            """, row)
        conn.commit()





if __name__=="__main__":

    # Parse arguments
    logger.info("Starting.")
    parser = argparse.ArgumentParser()

    parser.add_argument("method", choices=["drr", "mrr", "dgr", "dmgr", "mgr", "mmgr", "ds", "dms"], help="the method of comparison : daily R-R or monthly R-R or daily G-R or daily mean G-R or monthly G-R or monthly mean G-R or daily shift or daily mean shift")
    parser.add_argument("begin_date", help="begin date or month concerned, format YYYYMM(DD)")
    parser.add_argument("end_date", help="begin date or month concerned, format YYYYMM(DD)")
    parser.add_argument("product_type_1", choices=RADAR_PRODUCTS_TYPES, help="type of the first product to compare")
    parser.add_argument("product_type_2", choices=(GAUGE_PRODUCTS_TYPES+RADAR_PRODUCTS_TYPES), help="type of the second product to compare")
    parser.add_argument("min_availability", type=float, help="minimum availability of the products during the period between 0 and 1")
    parser.add_argument("-r1", "--radar1", default=None, help="radar corresponding to the first product")
    parser.add_argument("-r2", "--radar2", default=None, help="radar corresponding to the second product")
    parser.add_argument("-p", "--min_precip_rate", type=float, action="append", default=[], help="minimum precipitation rate in mm/hr, can be set multiple times, default %(default)s")
    parser.add_argument("-g", "--additional-gauge-network", action="append", default=[], help="additional gauge network to use")

    args = parser.parse_args()
    logger.debug(f"Parsed args: {args}.")



    # Verify the radar specification
    if scale_from_product_name(args.product_type_1) == "single" and args.radar1 is None:
        logger.error("Radar 1 is not specified.")
        sys.exit(1)
    if args.product_type_2 in RADAR_PRODUCTS_TYPES \
            and scale_from_product_name(args.product_type_2) == "single" \
            and args.radar2 is None:
        logger.error("Radar 2 is not specified.")
        sys.exit(1)
    


    # Launch the function
    if args.method == "drr":
        logger.debug("Selected method: daily R-R")
        day = datetime.date.strptime(args.begin_date, "%Y%m%d")
        end_day = datetime.date.strptime(args.end_date, "%Y%m%d")
        logger.debug(f"Period : {day} -> {end_day}")

        while day <= end_day:
            logger.info(f"Processing day {day}.")
            try:
                compare_r_r_daily(day.year, day.month, day.day, \
                                    args.min_availability, args.min_precip_rate, \
                                    args.product_type_1, args.product_type_2, \
                                    args.radar1, args.radar2)
            except Exception:
                logger.error(f"Error in compare_r_r_daily. Skipping day {day}.\n{traceback.format_exc()}")

            day += datetime.timedelta(days=1)
    
    elif args.method == "mrr":
            logger.debug("Selected method: monthly R-R")
            month = datetime.date.strptime(args.begin_date, "%Y%m")
            end_month = datetime.date.strptime(args.end_date, "%Y%m")
            logger.debug(f"Period : {month.strftime("%Y%m")} -> {end_month.strftime("%Y%m")}")
    
            while month <= end_month:
                logger.info(f"Processing month {month}.")
                try:
                    r_r_monthly_from_daily(month.year, month.month, \
                                        args.min_availability, args.min_precip_rate, \
                                        args.product_type_1, args.product_type_2, \
                                        args.radar1, args.radar2)
                except Exception:
                    logger.error(f"Error in r_r_monthly_from_daily. Skipping month {month}.\n{traceback.format_exc()}")
    
                if month.month==12:
                    month = datetime.date(month.year+1, 1, 1)
                else:
                    month = datetime.date(month.year, month.month+1, 1)

    elif args.method == "dgr":
        logger.debug("Selected method: daily G-R")
        day = datetime.date.strptime(args.begin_date, "%Y%m%d")
        end_day = datetime.date.strptime(args.end_date, "%Y%m%d")
        logger.debug(f"Period : {day} -> {end_day}")

        while day <= end_day:
            logger.info(f"Processing day {day}.")
            try:
                compare_g_r_daily(day.year, day.month, day.day, \
                                    args.min_availability, args.min_precip_rate, \
                                    args.product_type_2, args.product_type_1, \
                                    args.radar1)
            except Exception:
                logger.error(f"Error in compare_g_r_daily. Skipping day {day}.\n{traceback.format_exc()}")

            day += datetime.timedelta(days=1)
    
    elif args.method == "dmgr":
        logger.debug("Selected method: daily mean G-R")
        day = datetime.date.strptime(args.begin_date, "%Y%m%d")
        end_day = datetime.date.strptime(args.end_date, "%Y%m%d")
        logger.debug(f"Period : {day} -> {end_day}")

        while day <= end_day:
            logger.info(f"Processing day {day}.")
            try:
                mean_g_r_daily(day.year, day.month, day.day, \
                                    args.min_availability, args.min_precip_rate, \
                                    args.product_type_2, args.product_type_1, \
                                    args.radar1)
            except Exception:
                logger.error(f"Error in mean_g_r_daily. Skipping day {day}.\n{traceback.format_exc()}")

            day += datetime.timedelta(days=1)
    
    elif args.method == "mgr":
        logger.debug("Selected method: monthly G-R")
        month = datetime.date.strptime(args.begin_date, "%Y%m")
        end_month = datetime.date.strptime(args.end_date, "%Y%m")
        logger.debug(f"Period : {month.strftime("%Y%m")} -> {end_month.strftime("%Y%m")}")

        while month <= end_month:
            logger.info(f"Processing month {month}.")
            try:
                compare_g_r_monthly(month.year, month.month, \
                                    args.min_availability, args.min_precip_rate, \
                                    args.product_type_2, args.product_type_1, \
                                    args.radar1)
            except Exception:
                logger.error(f"Error in compare_g_r_monthly. Skipping month {month}.\n{traceback.format_exc()}")
            
            if month.month==12:
                month = datetime.date(month.year+1, 1, 1)
            else:
                month = datetime.date(month.year, month.month+1, 1)
    
    elif args.method == "mmgr":
        logger.debug("Selected method: monthly mean G-R")
        month = datetime.date.strptime(args.begin_date, "%Y%m")
        end_month = datetime.date.strptime(args.end_date, "%Y%m")
        logger.debug(f"Period : {month.strftime("%Y%m")} -> {end_month.strftime("%Y%m")}")

        while month <= end_month:
            logger.info(f"Processing month {month}.")
            try:
                mean_g_r_monthly(month.year, month.month, \
                                    args.min_availability, args.min_precip_rate, \
                                    args.product_type_2, args.product_type_1, \
                                    args.radar1)
            except Exception:
                logger.error(f"Error in mean_g_r_monthly. Skipping month {month}.\n{traceback.format_exc()}")
            
            if month.month==12:
                month = datetime.date(month.year+1, 1, 1)
            else:
                month = datetime.date(month.year, month.month+1, 1)
    
    elif args.method == "ds":
        logger.debug("Selected method: daily shift")
        day = datetime.date.strptime(args.begin_date, "%Y%m%d")
        end_day = datetime.date.strptime(args.end_date, "%Y%m%d")
        logger.debug(f"Period : {day} -> {end_day}")

        while day <= end_day:
            logger.info(f"Processing day {day}.")
            try:
                g_r_synchronization_daily(day.year, day.month, day.day, \
                                    args.min_availability, \
                                    args.product_type_2, args.product_type_1, \
                                    args.radar1)
            except Exception:
                logger.error(f"Error in g_r_synchronzation_daily. Skipping day {day}.\n{traceback.format_exc()}")

            day += datetime.timedelta(days=1)
    
    elif args.method == "dms":
        logger.debug("Selected method: daily mean shift")
        day = datetime.date.strptime(args.begin_date, "%Y%m%d")
        end_day = datetime.date.strptime(args.end_date, "%Y%m%d")
        logger.debug(f"Period : {day} -> {end_day}")

        while day <= end_day:
            logger.info(f"Processing day {day}.")
            try:
                g_r_synchronization_daily_mean(day.year, day.month, day.day, \
                                    args.min_availability, \
                                    [args.product_type_2]+args.additional_gauge_network, args.product_type_1, \
                                    args.radar1)
            except Exception:
                logger.error(f"Error in g_r_synchronization_daily_mean. Skipping day {day}.\n{traceback.format_exc()}")

            day += datetime.timedelta(days=1)