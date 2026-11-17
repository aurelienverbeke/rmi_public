from typing import Any

import numpy as np
from scipy.signal import convolve2d

##########
# CONSTANTS
##########

KE = 4/3
EARTH_MEAN_RADIUS = 6371
EARTH_EFFECTIVE_RADIUS = float(EARTH_MEAN_RADIUS * KE)

RHOHV_THRESHOLD_RAIN = 0.98





##########
# NON RADAR-RELATED FUNCTIONS
##########

def apply_none_mask(scans : list[np.ndarray[tuple[int, int], np.dtype[Any]]], mask : np.ndarray[tuple[int, int], np.dtype[np.bool_]]) \
        -> list[np.ndarray[tuple[int, int], np.dtype[Any]]]:
    """
        For all scans, sets all pixels to none if mask is True

        Parameters
        ----------
        scans : list of numpy.ndarray or tuple of numpy.ndarray
            Scans for which the mask must be applied
        mask : numpy.ndarray[bool]
            Mask, must have the same size as all scans.

        Returns
        -------
        type of `scans`
            Noned scans.
    """

    for i in range(len(scans)):
        scans[i][mask] = None

    return scans




def filter_rows_or_cols(scans : list[np.ndarray[tuple[int, int], np.dtype[Any]]], selection : np.ndarray[tuple[int], np.dtype[np.bool_]], axis : int, keep : bool) \
        -> list[np.ndarray[tuple[int, int], np.dtype[Any]]]:
    """
        For all scans, remove/keep rows/columns given in `selection`.

        Parameters
        ----------
        scans : list of numpyp.ndarray or tuple of numpy.ndarray
            Scans for which apply filter.
        selection : numpy.ndarray[bool]
            Rows/columns that will be removed/kept.
        axis : {0, 1}
            0 for working on rows, 1 for columns.
        keep : bool
            True for keeping selected rows/columns, False for removing.

        Returns
        -------
            type of `scans`
                Filtered scans.
    """

    for i in range(len(scans)):
        if keep:
            if axis==0:
                scans[i] = scans[i][selection,:]
            elif axis==1:
                scans[i] = scans[i][:,selection]
        else:
            if axis==0:
                scans[i] = scans[i][~selection,:]
            elif axis==1:
                scans[i] = scans[i][:,~selection]

    return scans





def angle_moving_mean(matrixes : list[np.ndarray[tuple[int, int], np.dtype[np.floating]]], mode : int, window_size : int = 25) \
        -> list[np.ndarray[tuple[int, int], np.dtype[np.floating]]]:
    """
        Makes a moving mean on each row of the given angle matrixes.

        Parameters
        ----------
        matrixes : list of numpy.ndarray or tuple of numpy.ndarray
            Matrixes on which do the moving means (size (m, n)). Angles must be in degrees.
        mode : {0, 1}
            0 for getting angles between 0deg and 360deg, 1 for between -180deg and 180deg.
        window_size : int, default=25
            Width of the window used for moving mean.

        Returns
        -------
        type of `matrixes`
            Meaned matrixes (size (m, n-`window_size`+1)). Angles are in degrees between 0 and 360.
    """

    window = np.ones((1, window_size))
    
    for i in range(len(matrixes)):
        sin_mean = convolve2d(np.sin(matrixes[i]*np.pi/180.), window, "valid") / window_size
        cos_mean = convolve2d(np.cos(matrixes[i]*np.pi/180.), window, "valid") / window_size
        
        angles = np.arctan2(sin_mean, cos_mean)*180./np.pi
        
        # arctan2 gives angles between -180deg and 180deg
        if mode == 0:
            angles[angles<0] += 360.

        matrixes[i] = angles
    
    return matrixes





def pad_matrix_right_nan(matrixes : list[np.ndarray[tuple[int, int], np.dtype[Any]]], n : int) \
        -> list[np.ndarray[tuple[int, int], np.dtype[Any]]]:
    """
        Pads the given matrixes with n Nan columns on the right.

        Parameters
        ----------
        matrixes : list of numpy.ndarray or tuple of numpy.ndarray
            Matrixes to pad.
        n : int
            Number of Nan columns to add.

        Returns
        -------
        type of `matrixes`
            Padded matrices.

        See also
        --------
        numpy.pad
    """
    
    for i in range(len(matrixes)):
        matrixes[i] = np.pad(matrixes[i], ((0,0), (0,n)), mode="constant", constant_values=np.nan)
    
    return matrixes





def substract_first_non_nan_by_row(matrixes : list[np.ndarray[tuple[int, int], np.dtype[Any]]]) \
        -> list[np.ndarray[tuple[int, int], np.dtype[Any]]]:
    """
        For each row of the given matrixes, substract the first found non-nan value.

        Parameters
        ----------
        matrixes : list of numpy.ndarray or tuple of numpy.ndarray
            The matrixes to work on.

        Returns
        -------
        type of `matrixes`
            The modified matrixes.
    """

    firsts = []

    for i in range(len(matrixes)):
        for row in matrixes[i]:
            not_nan_mask = ~np.isnan(row)
            if np.any(not_nan_mask):
                firsts.append(np.mean(row[not_nan_mask][:10]))
        matrixes[i] -= np.mean(firsts)

    return matrixes





def angles_median(angles : np.ndarray[Any, np.dtype[np.floating]], mode : int) -> float:
    """
        Computes the median of the given angles.
        Gets the median of both cosines and sines of angles, then uses arctan2.

        Parameters
        ----------
        angles : numpy.ndarray
            The angles in deg.
        mode : {0, 1}
            0 for getting angles between 0deg and 360deg, 1 for between -180deg and 180deg.

        Returns
        -------
        float
            The computed median of the angles in deg.

        Notes
        -----
        NaN values are not took into consideration.
    """

    cos_median = np.nanmedian(np.cos(angles*np.pi/180.))
    sin_median = np.nanmedian(np.sin(angles*np.pi/180.))

    angles_median = np.arctan2(sin_median, cos_median)*180./np.pi
    
    # arctan2 gives angles between -180deg and 180deg
    if mode == 0 and angles_median < 0:
        angles_median += 360.

    return angles_median





def weighted_angle_mean(angles : np.ndarray[Any, np.dtype[np.floating]], weights : np.ndarray[Any, np.dtype[np.floating]], mode : int) -> float:
    """
        Computes a weighted mean over the given angles.
        Gets the mean of both cosines and sines of angles, then uses arctan2.

        Parameters
        ----------
        angles : numpy.ndarray
            The angles is deg.
        weights : numpy.ndarray
            The weights. Must be same size as `angles`.
        mode : {0, 1}
            0 for getting angles between 0deg and 360deg, 1 for between -180deg and 180deg.

        Returns
        -------
        float
            The computed mean of the angles in deg.
    """

    total_weights = np.sum(weights)

    cos_mean = np.nansum(np.cos(angles*np.pi/180.)*weights) / total_weights
    sin_mean = np.nansum(np.sin(angles*np.pi/180.)*weights) / total_weights

    angles_mean = np.arctan2(sin_mean, cos_mean)*180./np.pi
    
    # arctan2 gives angles between -180deg and 180deg
    if mode == 0 and angles_mean < 0:
        angles_mean += 360.

    return angles_mean




##########
# RADAR-RELATED FUNCTIONS
##########

def get_distances_heights(bin_res : float, n_bins : int, elevation : float = 0., altitude : float = 0.) \
        -> tuple[np.ndarray[tuple[int], np.dtype[np.floating]], np.ndarray[tuple[int], np.dtype[np.floating]]]:
    """
        Computes the distance and height (altitude) of each gate center.

        Parameters
        ----------
        bin_res : float
            Gate resolution in km.
        n_bins : int
            Number of bins in a ray.
        elevation : float, default=0.0
            Elevation angle of the antenna in deg.
        altitude : float, default=0.0
            Altitude of the radar antenna in m.

        Returns
        -------
        numpy.ndarray
            Distance from the antenna of each gate center (`n_bins`,).
        numpy.ndarray
            Altitude of each gate center (`n_bins`,).

        See also
        --------
        wradlib.georef.misc.bin_altitude

        Notes
        -----
        For heights, uses formula 2.28b given in [1]

        References
        ----------
        [1] Doviak and Zrnic, *Doppler radar and weather observations*, Second edition, Academic press, p. 21, 1993.
    """

    distances = np.linspace(bin_res/2, (n_bins-1/2)*bin_res, n_bins)
    heights = altitude/1000. + np.sqrt(distances**2 + EARTH_EFFECTIVE_RADIUS**2 + 2*distances*EARTH_EFFECTIVE_RADIUS*np.sin(elevation*np.pi/180)) - EARTH_EFFECTIVE_RADIUS
    
    return distances, heights





def phidp0_from_phidp_rhohv(phidp : np.ndarray[tuple[int, int], np.dtype[np.floating]], rhohv : np.ndarray[tuple[int, int], np.dtype[np.floating]], n_first_gates : int = 20) -> float:
    """
        Compute initial PhiDP on first gates of precipitation.
        Simple mean on whole rain pixels around the radar.

        Parameters
        ----------
        phidp : numpy.ndarray
            Phidp radial matrix.
        rhohv : numpy.ndarray
            Rhohv radial matrix.
        n_first_gates : int, default=20
            Number of gates around the radar used to compute initial PhiDP.

        Returns
        -------
        float
            Initial PhiDP.

        Notes
        -----
        `phidp` and `rhohv` must have the same size and resolution.
    """

    phidp_first_5_km = phidp[:,:n_first_gates]
    rhohv_first_5_km = rhohv[:,:n_first_gates]

    phidps = phidp_first_5_km[rhohv_first_5_km > RHOHV_THRESHOLD_RAIN]

    cos_mean = np.nanmean(np.cos(phidps*np.pi/180.))
    sin_mean = np.nanmean(np.sin(phidps*np.pi/180.))

    angles_mean = np.arctan2(sin_mean, cos_mean)*180./np.pi
    
    # arctan2 gives angles between -180deg and 180deg
    if angles_mean < 0:
        angles_mean += 360.

    return angles_mean





def find_ray_rain_path(ray : np.ndarray[tuple[int], np.dtype[np.bool_]], min_gates_number : int) -> np.ndarray[tuple[int], np.dtype[np.bool_]]:
    """
        Find the most adapted rain path in a ray.
        Conditions:
            - closest to the radar
            - biggest range of consecutive valid pixels
            - max 5% missing / invalid points in path
            - min `min_gates_number` gates length
        Tests all paths by increasing begin index and decreasing length, until it finds one path, which hence is the best.

        Parameters
        ----------
        ray : numpy.ndarray[bool]
            The ray to find the rain path in. Rain pixels should be set to `True`.
        min_gates_number : int
            The minimal number of gates for the rain path length.

        Returns
        -------
        numpy.ndarray[bool]
            Boolean ray where the rain path pixels are set to True (same size as `ray`).
            If no path is found, returns a full-False boolean ray.
    """

    for i_begin in range(len(ray)-min_gates_number+1):
        if not ray[i_begin]:
            # The first pixel is not valid
            continue

        for length in reversed(range(min_gates_number, len(ray)-i_begin)):
            if not ray[i_begin+length]:
                # The last pixel is not valid
                continue
            
            subray = ray[i_begin:i_begin+length]
            ratio = np.count_nonzero(~subray) / length # Ratio of False values
            
            if ratio < 0.05:
                identified_path = np.array([False]*i_begin + [True]*length + [False]*(len(ray)-length-i_begin))
                return identified_path
    
    # No path found
    return np.full(len(ray), False)
