import multiprocessing
import os
import sys
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from viscalmon.general.io.radar import open_rainbow_pandas
from viscalmon.general.utils import (
    angle_moving_mean,
    apply_none_mask,
    filter_rows_or_cols,
    find_ray_rain_path,
    get_distances_heights,
    pad_matrix_right_nan,
    phidp0_from_phidp_rhohv,
    substract_first_non_nan_by_row,
)

RHOHV_THRESHOLD_RAIN = 0.98
RHOHV_THRESHOLD_PRECIP = 0.9
PHIDP_THRESHOLD = 12.
MIN_D = 1 # in km, from radar
MAX_H = 3 # in km, from sea level
MAX_NONVALID_DATA_IN_RAY_RATIO = 0.05
MIN_RAIN_PATH_LENGTH = 15 #km

MAX_NB_PROCESSES = 64

SHOW_PIXELS_USED = False

MOVING_AVERAGE_WINDOW_SIZE = 25





radar = sys.argv[1]
date_start = sys.argv[2]
date_end = sys.argv[3]
rainbow_files = sys.argv[4:]





def compute_by_date(data_by_date, concat_arrays_size_distance, alt):
    phidps_for_comparison = pd.DataFrame(columns=["elevation", "obs", "th_ryzhkov", "th_gourley"])
    phidps_for_comparison = phidps_for_comparison.astype({"elevation":"Float32", "obs":"object", "th_ryzhkov":"object", "th_gourley":"object"})

    for elevation in data_by_date["elevation"].drop_duplicates():
        # HERE : Reject entire scan if mean Z at vertical incidence from 840 to 2760 m in altitude > 20dBZ
        # Before, need to retrieve vertical Z scan (second open_rainbow with corresponding filenames, that we therefore need to pass to the python script from the bash script)



        data_by_date_elevation = data_by_date[data_by_date["elevation"]==elevation]

        # Skip if missing Z or Zdr or PhiDP
        z = data_by_date_elevation.loc[data_by_date_elevation["moment"]=="dBZ"]
        zdr = data_by_date_elevation.loc[data_by_date_elevation["moment"]=="ZDR"]
        phidp = data_by_date_elevation.loc[data_by_date_elevation["moment"]=="uPhiDP"]
        rhohv = data_by_date_elevation.loc[data_by_date_elevation["moment"]=="RhoHV"]
        if z.empty or zdr.empty or phidp.empty or rhohv.empty:
            print("Missing one moment.")
            continue

        z = z.iloc[0]
        zdr = zdr.iloc[0]
        phidp = phidp.iloc[0]
        rhohv = rhohv.iloc[0]

        n_bins = z["n_bins"]
        bin_res = z["bin_res"]



        if SHOW_PIXELS_USED:
            image_mask = np.full((*z["data"].shape, 4), [0, 0, 0, 255])



        # HERE : Zdr offsets at vertical incidence AND with empirical mask
        # Before, need to retrieve vertical Zdr scan (second open_rainbow with corresponding filenames, that we therefore need to pass to the python script from the bash script)



        # Remove no-data pixels
        nodata_mask = z["nodata_mask"] | zdr["nodata_mask"] | phidp["nodata_mask"] | rhohv["nodata_mask"]
        z["data"], zdr["data"], phidp["data"] = apply_none_mask([z["data"], zdr["data"], phidp["data"]], nodata_mask)
        if SHOW_PIXELS_USED:
            image_mask[nodata_mask,:] = 255

        
        
        # Remove points that are not rain (RhoHV < RHOHV_THRESHOLD_RAIN)
        rain_mask = rhohv["data"]<RHOHV_THRESHOLD_RAIN

        # Limit to PHIDP_THRESHOLD deg phase rotation
        phidp0 = phidp0_from_phidp_rhohv(phidp["data"], rhohv["data"])
        angle_diff = (phidp["data"] - phidp0 + 180) % 360 - 180
        rain_atten_mask = rain_mask | (angle_diff>PHIDP_THRESHOLD)
        
        nodata_rain_atten_mask = nodata_mask | rain_atten_mask # could be zdr or phidp as well, all have the same
        
        if SHOW_PIXELS_USED:
            image_mask[rain_atten_mask & ~nodata_mask] = [50, 200, 50, 255]

        
        
        # Smooth mask
        #window = np.ones((1, 10))
        #nodata_rain_atten_mask_smoothed = (scsig.convolve2d(nodata_rain_atten_mask.astype(np.int32), window, "same") / 10) > 0.5
        #nodata_rain_atten_mask_smoothed = nodata_rain_atten_mask_smoothed | nodata_mask # restore no-data pixels lost during smoothing
        nodata_rain_atten_mask_smoothed = nodata_rain_atten_mask
        #if SHOW_PIXELS_USED:
        #    image_mask[~nodata_rain_atten_mask_smoothed & nodata_rain_atten_mask] = [30, 150, 255, 255]



        # Presence of partially melted or frozen hydrometeors : altitude < MAX_H km
        # Also limit distance from radar > MIN_D
        distances, heights = get_distances_heights(bin_res, n_bins, elevation, alt)

        dist_height_mask = (MIN_D<=distances) & (heights<=MAX_H)
        if np.count_nonzero(dist_height_mask) < MOVING_AVERAGE_WINDOW_SIZE:
            continue

        dist_mask_2D = np.full(z["data"].shape, True)
        dist_mask_2D[:,dist_height_mask] = False
        nodata_rain_atten_mask_smoothed_dist = nodata_rain_atten_mask_smoothed | dist_mask_2D



        # Recognize rain paths
        # > 15km
        # Min 50 gates
        # Max 10% missing / non-valid data
        rain_paths = np.apply_along_axis(find_ray_rain_path, 1, ~nodata_rain_atten_mask_smoothed_dist, int(MIN_RAIN_PATH_LENGTH/bin_res))
        
        if SHOW_PIXELS_USED:
            image_rain_paths = np.full((*z["data"].shape, 4), [255, 255, 255, 100])
            image_rain_paths[~nodata_rain_atten_mask_smoothed_dist] = [0, 0, 150, 100]
            image_rain_paths[rain_paths,3] = 255

        z["data"], zdr["data"], phidp["data"], rhohv["data"] = apply_none_mask([z["data"], zdr["data"], phidp["data"], rhohv["data"]], ~rain_paths | nodata_rain_atten_mask_smoothed_dist)



        # Remove ray if
        path_n_bins = np.count_nonzero(rain_paths, axis=1)
        
        # Hail presence : Z > 50dB for one precipitation pixel in the rain path
        rows_to_remove = np.any((z["data"]>50.) & (rhohv["data"]>RHOHV_THRESHOLD_PRECIP), axis=1)

        # Too strong rain : more than 20% rain pixels with Z>30dB
        rows_to_remove = rows_to_remove | (np.count_nonzero((z["data"]>30.) & (rhohv["data"]>RHOHV_THRESHOLD_RAIN), axis=1) > 0.2*path_n_bins)
        
        # Mie scattering effects : Zdr > 3.5dB for one precipitation pixel in the ray
        rows_to_remove = rows_to_remove | np.any((zdr["data"]>3.5) & (rhohv["data"]>RHOHV_THRESHOLD_PRECIP), axis=1)
        
        # More than 5% non-precipitating echoes IN PATH
        rows_to_remove = rows_to_remove | (np.count_nonzero(rhohv["data"]<RHOHV_THRESHOLD_PRECIP, axis=1) > 0.05*path_n_bins)
        
        z["data"], zdr["data"], phidp["data"], rhohv["data"], nodata_mask, nodata_rain_atten_mask_smoothed_dist \
                = filter_rows_or_cols([z["data"], zdr["data"], phidp["data"], rhohv["data"], nodata_mask, nodata_rain_atten_mask_smoothed_dist], rows_to_remove, axis=0, keep=False)

        if SHOW_PIXELS_USED:
            rows_removed_indices = np.where(rows_to_remove)[0]
            for i, k in enumerate(rows_removed_indices):
                image_mask[k, nodata_mask[i]] = [255, 0, 0, 100]
                image_mask[k, ~nodata_mask[i]] = [255, 0, 0, 150]
                image_rain_paths[k,:,3] = 100

        
        
        # Compute Kdp from Z and Zdr
        freq_ratio_5_5 = z["freq"]/5500
        freq_ratio_5_6 = z["freq"]/5600
        z_lin = 10**(0.1*(z["data"]))
        f_zdr_ryzhkov = 10**(-5) * (6.7 - 4.42*zdr["data"] + 2.16*zdr["data"]**2 - 0.404*zdr["data"]**3)
        f_zdr_gourley = 10**(-5) * (6.746 - 2.97*zdr["data"] + 0.711*zdr["data"]**2 - 0.079*zdr["data"]**3)
        theorical_kdp_ryzhkov = z_lin * f_zdr_ryzhkov * freq_ratio_5_5
        theorical_kdp_gourley = z_lin * f_zdr_gourley * freq_ratio_5_6

        # Compute PhiDP from Kdp
        theorical_phidp_ryzhkov = 2 * np.nancumsum(theorical_kdp_ryzhkov, axis=1) * bin_res
        theorical_phidp_gourley = 2 * np.nancumsum(theorical_kdp_gourley, axis=1) * bin_res
        theorical_phidp_ryzhkov, theorical_phidp_gourley = apply_none_mask([theorical_phidp_ryzhkov, theorical_phidp_gourley], nodata_rain_atten_mask_smoothed_dist) # nancumsum replaces nan with 0
        
        # Initial PhiDP = 0
        theorical_phidp_ryzhkov, theorical_phidp_gourley, phidp["data"] = substract_first_non_nan_by_row([theorical_phidp_ryzhkov, theorical_phidp_gourley, phidp["data"]])
        #phidp["data"] -= phidp0 

        # Moving average
        theorical_phidp_ryzhkov, theorical_phidp_gourley, phidp["data"] = angle_moving_mean([theorical_phidp_ryzhkov, theorical_phidp_gourley, phidp["data"]], 1)
        
        
        
        # To see pixels used for each scan
        if SHOW_PIXELS_USED and elevation==0.9:
            fig = plt.figure(figsize=(20, 5))
            axs = fig.subplots(1, 2)

            legend_elements = [
                Patch(facecolor=(0, 0, 0, 1), edgecolor='black', label='Valid used pixel'),
                Patch(facecolor=(0.2, 0.78, 0.2, 1), edgecolor='black', label='Removed pixels'),
                #Patch(facecolor=(0.12, 0.59, 1, 1), edgecolor='black', label='Unvalid added pixels after smoothing'),
                Patch(facecolor=(1, 0, 0, 0.59), edgecolor='black', label='Removed ray'),
                Patch(facecolor=(1, 1, 1, 1), edgecolor='black', label='Unavailable data')
            ]
            
            axs[0].imshow(image_mask)
            axs[0].set_ylabel("Ray number")
            axs[0].set_xlabel("Bin number")
            axs[0].set_title("Mask")
            axs[0].legend(handles=legend_elements)
            
            axs[1].imshow(image_rain_paths)
            axs[1].set_ylabel("Ray number")
            axs[1].set_xlabel("Bin number")
            axs[1].set_title("Rain paths")
            
            fig.subplots_adjust(0.05, 0.03, 0.95, 0.97, 0.2, 0.2)
            plt.show()



        # Add columns with nan if needed
        rays_len = phidp["data"].shape[1]
        if rays_len < max_n_bins:
            theorical_phidp_ryzhkov, theorical_phidp_gourley, phidp["data"] = pad_matrix_right_nan([theorical_phidp_ryzhkov, theorical_phidp_gourley, phidp["data"]], concat_arrays_size_distance-rays_len)



        # Concatenate with other elevations and scans
        phidps_for_comparison.loc[len(phidps_for_comparison)] = [elevation, phidp["data"], theorical_phidp_ryzhkov, theorical_phidp_gourley]

    return phidps_for_comparison


        


# Quit here if results already existing
fig_file_name = f"{os.environ['DIR_Z_CONSISTENCY']}{radar}_{date_start}_{date_end}.png"
if os.path.isfile(fig_file_name):
    print(f"Figure {fig_file_name} already existing")
    sys.exit(0)



# Open rainbow files
data, _, _, alt = open_rainbow_pandas(rainbow_files)



# Stop here if different bin resolutions
# We could adapt statistics phase
# But too complicated for now and not necessary
if data["bin_res"].unique().size != 1:
    print("Different bin resolutions. Aborting.", file=sys.stderr)
    sys.exit(1)
bin_res = data["bin_res"][0]



# Keep elevations <= 3 deg
data = data[data["elevation"] <= 3.0]



max_n_bins = data["n_bins"].max()

# Distances corresponding to values after moving average
distances = np.linspace(bin_res/2, (max_n_bins-1/2)*bin_res, max_n_bins)
if MOVING_AVERAGE_WINDOW_SIZE%2 == 0:
    n_skipped = MOVING_AVERAGE_WINDOW_SIZE//2
    distances = distances[n_skipped-1 : -n_skipped] + bin_res/2
else:
    n_skipped = (MOVING_AVERAGE_WINDOW_SIZE-1) // 2
    distances = distances[n_skipped : -n_skipped]

concat_arrays_size_distance = max_n_bins - MOVING_AVERAGE_WINDOW_SIZE + 1



datas_by_date = [ data[data["date"]==date] for date in data["date"].drop_duplicates() ]
nb_processes = min(os.process_cpu_count(), MAX_NB_PROCESSES)
with multiprocessing.Pool(processes=nb_processes) as pool:
    results = pool.starmap(compute_by_date, zip(datas_by_date, [concat_arrays_size_distance]*len(datas_by_date), [alt]*len(datas_by_date)), chunksize=max(len(datas_by_date)//nb_processes, 1))
phidps_for_comparison = pd.concat(results).groupby("elevation").agg(np.vstack).reset_index()

# Concatenate all elevations
phidps_for_comparison.loc[len(phidps_for_comparison)] = ["All", np.vstack(phidps_for_comparison["obs"]), np.vstack(phidps_for_comparison["th_ryzhkov"]), np.vstack(phidps_for_comparison["th_gourley"])]

# Compute differences th_ryzhkov-obs and th_gourley-obs
phidps_for_comparison["th_ryzhkov-obs"] = phidps_for_comparison["th_ryzhkov"] - phidps_for_comparison["obs"]
phidps_for_comparison["th_gourley-obs"] = phidps_for_comparison["th_gourley"] - phidps_for_comparison["obs"]




# Plots

n_elevations = phidps_for_comparison["elevation"].drop_duplicates().size
n_rows_plot = int(np.floor(np.sqrt(n_elevations)))
n_columns_plot = int(np.ceil(np.sqrt(n_elevations)))
fig = plt.figure(figsize=(n_columns_plot*10, n_rows_plot*10))
axs = fig.subplots(n_rows_plot, n_columns_plot)

for i_elevation, elevation in enumerate(phidps_for_comparison["elevation"].unique()):
    ax = axs[i_elevation//n_columns_plot, i_elevation%n_columns_plot]

    ax_n_pixels = ax.twinx()

    phidps_for_comparison_elevation = phidps_for_comparison[phidps_for_comparison["elevation"]==elevation].iloc[0]

    ax.plot(distances, np.nanmean(phidps_for_comparison_elevation["th_ryzhkov-obs"], axis=0), label=r"$\Phi_{DP}^{\mathrm{th, ryzhkov}} - \Phi_{DP}^{\mathrm{obs}}$ mean")
    ax.plot(distances, np.nanmean(phidps_for_comparison_elevation["th_gourley-obs"], axis=0), label=r"$\Phi_{DP}^{\mathrm{th, gourley}} - \Phi_{DP}^{\mathrm{obs}}$ mean")
    ax.plot(distances, np.nanmedian(phidps_for_comparison_elevation["th_ryzhkov-obs"], axis=0), label=r"$\Phi_{DP}^{\mathrm{th, ryzhkov}} - \Phi_{DP}^{\mathrm{obs}}$ median")
    ax.plot(distances, np.nanmedian(phidps_for_comparison_elevation["th_gourley-obs"], axis=0), label=r"$\Phi_{DP}^{\mathrm{th, gourley}} - \Phi_{DP}^{\mathrm{obs}}$ median")
    ax_n_pixels.bar(distances, np.count_nonzero(~np.isnan(phidps_for_comparison_elevation["obs"]), axis=0), alpha=0.2, width=bin_res)

    ax.set_xlabel("Distance (km)")
    ax.set_ylim(-10, 10)
    ax.set_ylabel("PhiDP (deg)")
    ax.legend()
    ax_n_pixels.set_ylabel("Number of pixels")
    ax.set_title(f"{elevation} deg")

fig.subplots_adjust(0.03, 0.03, 0.97, 0.9, 0.2, 0.2)
fig.suptitle(f"PhiDP distribution for {radar.capitalize()} radar\nFrom {datetime.strptime(date_start, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M')} to {datetime.strptime(date_end, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M')}\nMin distance {MIN_D:.1f} km\nMax height {MAX_H:.1f} km")

fig.savefig(fig_file_name, dpi=100)
print(f"Figure saved in {fig_file_name}")

