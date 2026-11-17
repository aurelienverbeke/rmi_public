import multiprocessing
import os
import sys
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from viscalmon.general.io.radar import open_rainbow_pandas
from viscalmon.general.utils import get_distances_heights

RHOHV_THRESHOLD = 0.99
PHIDP_THRESHOLD = 10.
MIN_Z = 14 #need int
MAX_Z = 30 #need int
MIN_D = 2 # in km, from radar
MAX_H = 3 # in km, from sea level
MAX_NB_PROCESSES = 64



radar = sys.argv[1]
date_start = sys.argv[2]
date_end = sys.argv[3]
rainbow_files = sys.argv[4:]



def compute_date_data_clean(data_by_date, alt):
    z_by_elevation = {}
    zdr_by_elevation = {}
    
    for elevation in data_by_date["elevation"].drop_duplicates():
        data_by_date_elevation = data_by_date[data_by_date["elevation"]==elevation]

        # Skip date if missing Z or Zdr
        z = data_by_date_elevation.loc[data_by_date_elevation["moment"]=="dBZ"]
        zdr = data_by_date_elevation.loc[data_by_date_elevation["moment"]=="ZDR"]
        phidp = data_by_date_elevation.loc[data_by_date_elevation["moment"]=="PhiDP"]
        rhohv = data_by_date_elevation.loc[data_by_date_elevation["moment"]=="RhoHV"]
        if z.empty or zdr.empty or rhohv.empty or phidp.empty:
            print("Missing Z or Zdr or RhoHV or PhiDP.")
            continue

        z = z.iloc[0]
        zdr = zdr.iloc[0]
        rhohv = rhohv.iloc[0]
        phidp = phidp.iloc[0]



        # Remove no-data points
        mask = z["nodata_mask"] | zdr["nodata_mask"] | rhohv["nodata_mask"] | phidp["nodata_mask"]

        # Remove points that are not rain (RhoHV < RHOHV_THRESHOLD)
        mask = mask | (rhohv["data"]<RHOHV_THRESHOLD)

        # Limit to PHIDP_THRESHOLD deg phase rotation if PhiDP available
        mask = mask | (phidp["data"]>PHIDP_THRESHOLD)

        # Limit to Z in [MIN_Z ; MAX_Z]dB
        mask = mask | (z["data"]<MIN_Z) | (z["data"]>MAX_Z)

        # Apply filter
        z["data"][mask] = None
        zdr["data"][mask] = None

        
        # Reduce to [min_distance ; max_height]
        n_bins = z["n_bins"]
        bin_res = z["bin_res"]
        distances, heights = get_distances_heights(bin_res, n_bins, elevation, alt)
        
        z["data"] = z["data"][:, (MIN_D<=distances) & (heights<=MAX_H)]
        zdr["data"] = zdr["data"][:, (MIN_D<=distances) & (heights<=MAX_H)]
        
        # Concatenation all pixmaps
        z_by_elevation[elevation] = z["data"].flatten()
        zdr_by_elevation[elevation] = zdr["data"].flatten()

    return z_by_elevation, zdr_by_elevation





# Quit here if results already existing
fig_file_name = f"{os.environ['DIR_ZDR_CONSISTENCY']}{radar}_{date_start}_{date_end}.png"
if os.path.isfile(fig_file_name):
    print(f"Figure {fig_file_name} already existing")
    sys.exit(0)



# Open rainbow files
data, _, _, alt = open_rainbow_pandas(rainbow_files)



# Compute data cleaning (missing values, attenuation, non-rain echoes...) for each 5-min date
datas_by_date = [ data[data["date"]==date] for date in data["date"].drop_duplicates() ]
nb_processes = min(os.process_cpu_count(), MAX_NB_PROCESSES)
with multiprocessing.Pool(processes=nb_processes) as pool:
    results = pool.starmap(compute_date_data_clean, zip(datas_by_date, [alt]*len(datas_by_date)), chunksize=max(len(datas_by_date)//nb_processes, 1))
z_concat = pd.DataFrame([ result[0] for result in results ]).sort_index(axis=1)
zdr_concat = pd.DataFrame([ result[1] for result in results ]).sort_index(axis=1)



# Concatenate all dates
z_concat = z_concat.apply(np.concatenate, axis=0)
zdr_concat = zdr_concat.apply(np.concatenate, axis=0)

# Concatenate all elevations
z_concat["All"] = np.concatenate(z_concat.values)
zdr_concat["All"] = np.concatenate(zdr_concat.values)



n_elevations = data["elevation"].drop_duplicates().size + 1 # +1 for all elevations together
n_rows_plot = int(np.floor(np.sqrt(n_elevations)))
n_columns_plot = int(np.ceil(np.sqrt(n_elevations)))
fig = plt.figure(figsize=(n_columns_plot*10, n_rows_plot*10))
axs = fig.subplots(n_rows_plot, n_columns_plot)



bounds = list(range(MIN_Z, MAX_Z+2, 2))
mean_z = [bound + 1 for bound in bounds[:-1]]



elevations = z_concat.keys().to_list()
# For each elevation and all elevations together
for i_elevation, elevation in enumerate(elevations):
    # Compute statistics
    """
    indices_sort_by_z = np.argsort(z_concat[elevation])
    z_concat[elevation] = np.take(z_concat[elevation], indices_sort_by_z)
    zdr_concat[elevation] = np.take(zdr_concat[elevation], indices_sort_by_z)
    """

    # Put all in a DataFrame for sorting, grouping...
    z_zdr = pd.DataFrame(data={"dBZ":z_concat[elevation], "ZDR":zdr_concat[elevation]}).dropna(subset="dBZ")
    z_zdr["dBZ_groups"] = pd.cut(z_zdr["dBZ"], bins=bounds, include_lowest=True)
    z_zdr_group_by_z = z_zdr.groupby("dBZ_groups", observed=False)
    mean = z_zdr_group_by_z.mean()["ZDR"]
    median = z_zdr_group_by_z.median()["ZDR"]
    number_points = z_zdr_group_by_z.count()["ZDR"]
    n_dates = len(data["date"].unique())



    # Make plots
    ax = axs[i_elevation//n_columns_plot, i_elevation%n_columns_plot]
    ax.plot([20, 22, 24, 26, 28, 30], [0.23, 0.27, 0.33, 0.4, 0.48, 0.56], label="Target") # for C-band, Ryzhkov&Zrnic 2019, table 6.3 page 155
    ax.plot(mean_z, mean, label="Measured mean")
    ax.plot(mean_z, median, label="Measured median")

    ax_number_points = ax.twinx()
    ax_number_points.bar(mean_z, number_points, alpha=0.2, width=1)
    ax_number_points.set_ylabel("Number of points")
    if elevation == "All":
        ax_number_points.set_ylim([0, n_dates*100000])
    else:
        ax_number_points.set_ylim([0, n_dates*10000])

    ax.legend(loc="upper right")
    ax.set_xlabel("Z (dBZ)")
    ax.set_ylabel("Zdr (dB)")
    ax.set_xlim([min(MIN_Z, 20), max(MAX_Z, 30)])
    ax.set_ylim([0, 2])
    ax.set_title(f"{elevation} deg")

fig.subplots_adjust(0.03, 0.03, 0.97, 0.9, 0.2, 0.2)
fig.suptitle(f"Z-Zdr distribution for {radar.capitalize()} radar\nFrom {datetime.strptime(date_start, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M')} to {datetime.strptime(date_end, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M')}\nMin distance {MIN_D:.1f} km\nMax height {MAX_H:.1f} km")

fig.savefig(fig_file_name, dpi=100)
print(f"Figure saved in {fig_file_name}")
