import numpy as np
from scipy.spatial import KDTree

from viscalmon.general.exceptions import ShapeError


class CachedInterpolator:
    """
        An interpolator adapted to interpolate radar or gauge data on a radar grid.

        Each grid defined by:
            - projection string
            - upper-left corner WGS84 coordinates
            - horizontal and vertical pixel resolution
            - horizontal and vertical pixels number
        is cached in the interpolator to be reused later.

        Notes
        -----
        Inspired from `wradlib.ipol.Nearest`
    """

    def __init__(self):
        """
            Constructor.
        """

        self.trees = {}
    





    def exists(self, proj : str, \
                lon0 : float, lat0 : float, \
                n_x_pixels : int, n_y_pixels : int, \
                x_pixel_res : float, y_pixel_res : float):
        """
            Indicates if a grid is already cached.

            Parameters
            ----------
            proj : str
                Projection string.
            
            lon0 : float
                Upper-left pixel WGS84 longitude.

            lat0 : float
                Upper-left pixel WGS84 latitude.

            n_x_pixels : int
                Horizontal number of pixels.

            n_y_pixels : int
                Vertical number of pixels.

            x_pixel_res : float
                Horizontal resolution of a pixel in kilometers.

            y_pixel_res : float
                Vertical resolution of a pixel in kilometers.

            Returns
            -------
            bool
                If the is already cached.
        """

        return (proj, lon0, lat0, n_x_pixels, n_y_pixels, x_pixel_res, y_pixel_res) in self.trees
    


    
    
    def add_interpolation_radar_grid(self, proj : str, \
                                    lons : np.ndarray[tuple[int], np.dtype[np.floating]], \
                                    lats : np.ndarray[tuple[int], np.dtype[np.floating]], \
                                    n_x_pixels : int, n_y_pixels : int, \
                                    x_pixel_res : float, y_pixel_res : float):
        """
            Adds an interpolation grid to he cache.
            
            Does nothing if the grid already exists.

            Parameters
            ----------
            proj : str
                Projection string.
            
            lons : float
                Pixels WGS84 longitudes. Shape (n,).

            lats : float
                Pixels WGS84 latitude. Shape (n,).

            n_x_pixels : int
                Horizontal number of pixels.

            n_y_pixels : int
                Vertical number of pixels.

            x_pixel_res : float
                Horizontal resolution of a pixel in kilometers.

            y_pixel_res : float
                Vertical resolution of a pixel in kilometers.
        """

        if lons.shape != lats.shape:
            raise ShapeError("Longitudes and latitudes shapes are different.")

        if len(lons.shape) != 1:
            raise ShapeError("Longitudes and latitudes arrays are not one-dimensional.")

        lons = lons.flatten()
        lats = lats.flatten()

        key = (proj, lons[0], lats[0], n_x_pixels, n_y_pixels, x_pixel_res, y_pixel_res)

        if not self.exists(*key):
            # Adapt shape for KDTree:
            # 1 row = 1 coord
            # 1 column = 1 point
            coords = np.vstack((lons, lats)).transpose()

            # Construct reference tree
            tree = KDTree(coords)

            self.trees[key] = tree
    




    def interpolated_indexes(self, key : tuple, lons : np.ndarray[tuple[int], np.dtype[np.floating]], lats : np.ndarray[tuple[int], np.dtype[np.floating]], max_distance : float) \
            -> tuple[np.ndarray[tuple[int], np.dtype[np.integer]], np.ndarray[tuple[int], np.dtype[np.integer]]]:
        """
            Gives the indexes of the corresponding pixels of `lons` and `lats` in the grid specified by `key`.

            Parameters
            ----------
            key : tuple
                See `exists()` parameters. Put in same order.

            lons : numpy.ndarray
                WGS84 longitudes of the positions to interpolate. Shape (m,).

            lats : numpy.ndarray
                WGS84 latitudes of the positions to interpolate. Shape (m,).
            
            max_distance : float
                Max distance between a point in `(lons, lats)` and its equivalent in the destination grid.

            Returns
            -------
            numpy.ndarray
                Indexes from `(lons, lats)`.
            
            numpy.ndarray
                Correponding indexes in the specified grid.
        """

        if not self.exists(*key):
            raise KeyError("The specified key doesn't exist in the cache.")
        
        if lons.shape != lats.shape:
            raise ShapeError("Longitudes and latitudes shapes are different.")

        if len(lons.shape) != 1:
            raise ShapeError("Longitudes and latitudes arrays are not one-dimensional.")
        
        # Returns distances and indexes of the nearest neighbor (from second set) for each point of the first set (flattened)
        distances, indexes = self.trees[key].query(np.vstack((lons, lats)).transpose(), workers=-1)

        mask_valid_distances = distances<=max_distance
        
        # Only keep indexes respecting distance < max_distance
        indexes_valid_data_src = np.nonzero(mask_valid_distances)[0]
        indexes_valid_data_dst = indexes[mask_valid_distances]

        return indexes_valid_data_src, indexes_valid_data_dst
