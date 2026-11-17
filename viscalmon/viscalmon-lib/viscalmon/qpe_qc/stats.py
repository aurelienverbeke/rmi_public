import logging
from typing import Literal, TypedDict

import numpy as np
from pyproj import Geod

from viscalmon.general.exceptions import ShapeError

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)





class StatsType(TypedDict):
    n_pixels : int
    mean_error : float
    mean_abs_error : float
    rmse : float
    median_error : float
    weighted_error : float
    cov : float
    var_values : float
    var_reference : float
    corr : float
    total_bias : float
    mean_bias : float
    median_bias : float
    weighted_bias : float
    scatter_score : float
    ratio_1_db : float
    ratio_2_db : float





def stats(min_precip_values : list[float], min_precip_value_behaviour : Literal["reference", "any"], \
            reference : np.ndarray[tuple[int], np.dtype[np.floating]], \
            values : np.ndarray[tuple[int], np.dtype[np.floating]]) \
            -> list[StatsType]:
    """
    Computes statistics on two sets : one for reference, one for values to compare.

    Parameters
    ----------
    min_precip_values : list of float
        Minimum pricipitation values, in mm.
    
    min_precip_value_behaviour : {'reference', 'any'}
        If the minimum precipitation value should be applied on reference data or any data. 
    
    reference : numpy.array
        Reference values. Shape (n,)

    values : numpy.array
        Values to compare to reference. Shape (n,)

    Returns
    -------
    list of StatsType
        For each minimum precipitation value those statistics:
        - Number of data couples used.
        - Mean error.
        - Mean absolute error.
        - Root mean square error.
        - Median error.
        - Weighted error.
        - Covariance.
        - `values` variance.
        - `reference` variance.
        - Correlation.
        - Total bias in dB.
        - Mean bias in dB.
        - Median bias in dB.
        - Weighted bias in dB.
        - Scatter score in dB.
        - Ratio of couples within 1dB.
        - Ratio of couples within 2dB.
        - Nash-Sutcliffe efficiency coefficient.

    Notes
    -----
    First, removes all nan values and corresponding values in the other set.
    """

    if min_precip_value_behaviour not in ["reference", "any"]:
        raise ValueError("Wrong minimum precipitation rate behaviour.")
    
    if values.shape != reference.shape:
        raise ShapeError("Longitudes and latitudes shapes are different.")

    if len(values.shape) != 1:
        raise ShapeError("Longitudes and latitudes arrays are not one-dimensional.")
    

    
    logger.info("Keeping only non-nan pairs.")
    both_non_nan = (~np.isnan(values)) & (~np.isnan(reference))

    values = np.copy(values)[both_non_nan]
    reference = np.copy(reference)[both_non_nan]



    results : list[StatsType] = []

    # Sorted for eliminating values gradually
    logger.info(f"Minimum precipitation values to process: {min_precip_values}")
    for min_precip_value in sorted(min_precip_values):
        logger.info(f"Processing minimum precipitation value {min_precip_value}")
        if min_precip_value_behaviour == "reference":
            reference_over_min = (reference >= min_precip_value)
            values = values[reference_over_min]
            reference = reference[reference_over_min]
        else:
            any_over_min = (reference >= min_precip_value) | (values >= min_precip_value)
            values = values[any_over_min]
            reference = reference[any_over_min]



        n = values.shape[0]

        if n == 0:
            logger.warning("No data remaining. Skipping.")
            results.append({
                "n_pixels" : 0,
                "mean_error" : np.nan,
                "mean_abs_error" : np.nan,
                "rmse" : np.nan,
                "median_error" : np.nan,
                "weighted_error" : np.nan,
                "cov" : np.nan,
                "var_values" : np.nan,
                "var_reference" : np.nan,
                "corr" : np.nan,
                "total_bias" : np.nan,
                "mean_bias" : np.nan,
                "median_bias" : np.nan,
                "weighted_bias" : np.nan,
                "scatter_score" : np.nan,
                "ratio_1_db" : np.nan,
                "ratio_2_db" : np.nan
            })
            continue
        
        
        
        difference = values - reference
        
        mean_error = np.mean(difference)

        median_error = np.median(difference)

        mean_abs_error = np.mean(np.absolute(difference))

        mse = np.sum(difference**2)/n
        rmse = np.sqrt(mse)



        indexes_sorted_difference = np.argsort(difference)
        sorted_reference = reference[indexes_sorted_difference]
        sorted_difference = difference[indexes_sorted_difference]

        reference_cum_sum = np.nancumsum(sorted_reference)
        reference_cum_sum_normalized = reference_cum_sum / reference_cum_sum[-1]

        index_q_50 = np.argmin(np.absolute(reference_cum_sum_normalized - 0.5))

        weighted_error = 10. * np.log10(sorted_difference[index_q_50])
        if weighted_error==np.inf or weighted_error==-np.inf:
            # Security if sorted_difference[index_q_50] = 0
            weighted_error = np.nan

        
        
        cov_matrix = np.cov(np.vstack((values, reference)))

        cov = cov_matrix[0, 1]
        var_values = cov_matrix[0, 0]
        var_reference = cov_matrix[1, 1]
        corr = cov/(np.sqrt(var_values*var_reference))




        total_bias = 10. * np.log10(np.sum(values)/np.sum(reference))
        if total_bias==np.inf or total_bias==-np.inf:
            # Security if sum(values) = 0 or sum(reference) = 0
            total_bias = np.nan

        values_over_reference = values/reference
        # Security if reference = 0
        values_over_reference[(values_over_reference==np.inf) | (values_over_reference==-np.inf)] = np.nan

        mean_bias = 10. * np.log10(np.mean(values_over_reference))
        if mean_bias==np.inf or mean_bias==-np.inf:
            # Security if mean(values_over_reference) = 0
            mean_bias = np.nan

        median_bias = 10. * np.log10(np.median(values_over_reference))
        if median_bias==np.inf or median_bias==-np.inf:
            # Security if median(values_over_reference) = 0
            median_bias = np.nan

        
        
        indexes_sorted_values_over_reference = np.argsort(values_over_reference)
        sorted_reference = reference[indexes_sorted_values_over_reference]
        sorted_values_over_reference = values_over_reference[indexes_sorted_values_over_reference]

        reference_cum_sum = np.nancumsum(sorted_reference)
        reference_cum_sum_normalized = reference_cum_sum / reference_cum_sum[-1]

        index_q_17 = np.argmin(np.absolute(reference_cum_sum_normalized - 0.17))
        index_q_50 = np.argmin(np.absolute(reference_cum_sum_normalized - 0.5))
        index_q_83 = np.argmin(np.absolute(reference_cum_sum_normalized - 0.83))

        weighted_bias = 10. * np.log10(sorted_values_over_reference[index_q_50])
        if weighted_bias==np.inf or weighted_bias==-np.inf:
            # Security if sorted_values_over_reference[index_q_50] = 0
            weighted_bias = np.nan

        scatter_score = 10. * np.log10(sorted_values_over_reference[index_q_83]) \
                            - 10. * np.log10(sorted_values_over_reference[index_q_17])
        if scatter_score==np.inf or scatter_score==-np.inf:
            # Security if sorted_values_over_reference[index_q_17] = 0 or sorted_values_over_reference[index_q_83] = 0
            scatter_score = np.nan
        
        
        
        values_over_reference_db = 10. * np.log10(values_over_reference)
        ratio_1_db = np.count_nonzero((-1 <= values_over_reference_db) & (values_over_reference_db <= 1))/n
        ratio_2_db = np.count_nonzero((-2 <= values_over_reference_db) & (values_over_reference_db <= 2))/n

        

        results.append({
            "n_pixels" : n,
            "mean_error" : mean_error,
            "mean_abs_error" : mean_abs_error,
            "rmse" : rmse,
            "median_error" : median_error,
            "weighted_error" : weighted_error,
            "cov" : cov,
            "var_values" : var_values,
            "var_reference" : var_reference,
            "corr" : corr,
            "total_bias" : total_bias,
            "mean_bias" : mean_bias,
            "median_bias" : median_bias,
            "weighted_bias" : weighted_bias,
            "scatter_score" : scatter_score,
            "ratio_1_db" : ratio_1_db,
            "ratio_2_db" : ratio_2_db
        })
    
    
    
    logger.debug("Returning")
    return results





def mean_stats(stats_list : list[StatsType]) -> StatsType:
    """
        Computes weighted mean statistics.
    
        Parameters
        ----------
        stats_list : list of StatsType
            Statistics groups.
    
        Returns
        -------
        StatsType
            See `stats()`.
    """

    if len(stats_list) > 0:
        # Make a dict of np arrays from a list of dicts
        concat_stats = { key : np.array([stats.get(key) for stats in stats_list]) for key in stats_list[0] }

        n_pixels = np.sum(concat_stats["n_pixels"])
        cov = np.nansum(concat_stats["cov"]*concat_stats["n_pixels"]) / n_pixels
        var_values = np.nansum(concat_stats["var_values"]*concat_stats["n_pixels"]) / n_pixels
        var_reference = np.nansum(concat_stats["var_reference"]*concat_stats["n_pixels"]) / n_pixels
        
        return {
            "n_pixels" : n_pixels,
            "mean_error" : np.nansum(concat_stats["mean_error"]*concat_stats["n_pixels"]) / n_pixels,
            "mean_abs_error" : np.nansum(concat_stats["mean_abs_error"]*concat_stats["n_pixels"]) / n_pixels,
            "rmse" : np.nansum(concat_stats["rmse"]*concat_stats["n_pixels"]) / n_pixels,
            "median_error" : np.nansum(concat_stats["median_error"]*concat_stats["n_pixels"]) / n_pixels,
            "weighted_error" : np.nansum(concat_stats["weighted_error"]*concat_stats["n_pixels"]) / n_pixels,
            "cov" : cov,
            "var_values" : var_values,
            "var_reference" : var_reference,
            "corr" : cov/np.sqrt(var_values*var_reference),
            "total_bias" : np.nansum(concat_stats["total_bias"]*concat_stats["n_pixels"]) / n_pixels,
            "mean_bias" : np.nansum(concat_stats["mean_bias"]*concat_stats["n_pixels"]) / n_pixels,
            "median_bias" : np.nansum(concat_stats["median_bias"]*concat_stats["n_pixels"]) / n_pixels,
            "weighted_bias" : np.nansum(concat_stats["weighted_bias"]*concat_stats["n_pixels"]) / n_pixels,
            "scatter_score" : np.nansum(concat_stats["scatter_score"]*concat_stats["n_pixels"]) / n_pixels,
            "ratio_1_db" : np.nansum(concat_stats["ratio_1_db"]*concat_stats["n_pixels"]) / n_pixels,
            "ratio_2_db" : np.nansum(concat_stats["ratio_2_db"]*concat_stats["n_pixels"]) / n_pixels
        }


    
    else:
        # No statistics given
        logger.warning("No statistics given.")

        return {
            "n_pixels" : 0,
            "mean_error" : np.nan,
            "mean_abs_error" : np.nan,
            "rmse" : np.nan,
            "median_error" : np.nan,
            "weighted_error" : np.nan,
            "cov" : np.nan,
            "var_values" : np.nan,
            "var_reference" : np.nan,
            "corr" : np.nan,
            "total_bias" : np.nan,
            "mean_bias" : np.nan,
            "median_bias" : np.nan,
            "weighted_bias" : np.nan,
            "scatter_score" : np.nan,
            "ratio_1_db" : np.nan,
            "ratio_2_db" : np.nan
        }





def mean_shift(shifts : np.ndarray[tuple[int], np.dtype[np.floating]],
                n_g_nonzeros : np.ndarray[tuple[int], np.dtype[np.integer]], \
                radar_lon : float | None = None,
                radar_lat : float | None = None,
                lons : np.ndarray[tuple[int], np.dtype[np.floating]] | None = None,
                lats : np.ndarray[tuple[int], np.dtype[np.floating]] | None = None) \
            -> tuple[int | None, int]:
    """
        Computes the mean shift for multiple rain gauges.

        Favors the gauges close to the radar and for which we have the biggest quantity of data.

        Parameters
        ----------
        shifts : numpy.ndarray
            Values of the shifts measurements.

        n_g_nonzeros : numpy.ndarray
            Number of valid gauge measurements corresponding to the shifts measurements.
        
        radar_lon : float, optional
            Radar WGS84 longitude.

        radar_lat : float, optional
            Radar WGS84 latitude.

        lons : numpy.ndarray, optional
            Longitudes of the shifts measurements.
        
        lats : numpy.ndarray, optional
            Latitudes of the shifts measurements.

        Returns
        -------
        int | None
            Mean shift.

        int
            Total number of valid gauge measurements.
    """

    if lons is not None and lats is not None and radar_lon is not None and radar_lat is not None:
        if len(lons) != len(lats) or len(lons) != len(shifts) or len(lons) != len(n_g_nonzeros):
            raise ValueError("The arrays don't have the same length.")

        if len(lons) == 0:
            return None, 0
        
        # Calculate distance between the gauges and the radar
        geod = Geod(ellps="WGS84")
        _, _, distances = geod.inv(np.full_like(lons, radar_lon), np.full_like(lats, radar_lat), lons, lats, radians=False)
        distances /= 1000. # In km to stay in a range of the inverse function which isn't too close to 0

        # Weight with number of data and inverse distance
        weights= n_g_nonzeros / distances
    
    else:
        # Only weight with number of data
        weights = n_g_nonzeros

    

    # Compute mean and total number of measurements used
    weights_sum = np.sum(weights)
    if weights_sum == 0:
        return None, 0
    else:
        total_mean_shift = int(np.nansum(shifts*weights)/weights_sum)
        total_n_g_nonzero = int(np.sum(n_g_nonzeros))
        return total_mean_shift, total_n_g_nonzero