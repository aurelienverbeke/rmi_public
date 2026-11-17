import os
import sys
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from viscalmon.general.io.radar import open_rainbow_pandas

RHOHV_THRESHOLD = 0.99
MIN_Z = 10 #need int
MAX_Z = 30 #need int
MIN_H = 1 # in km, from sea level
MAX_H = 3 # in km, from sea level



radar = sys.argv[1]
date_start = sys.argv[2]
date_end = sys.argv[3]
rainbow_files = sys.argv[4:]



# Quit here if results already existing
fig_file_name = f"{os.environ['DIR_ZDR_VERTICAL']}{radar}_{date_start}_{date_end}.png"
if os.path.isfile(fig_file_name):
    print(f"Figure {fig_file_name} already existing")
    sys.exit(0)



# Open rainbow files
data, _, _, alt = open_rainbow_pandas(rainbow_files)

# Drop elevation column, all 90deg
data.drop("elevation", inplace=True, axis=1)


# If different characteristics regarding size, stop there
columns_to_verify = ["n_bins", "n_rays", "bin_res"]
for column_to_verify in columns_to_verify:
    if data[column_to_verify].drop_duplicates().shape[0] > 1:
        print(f"Column {column_to_verify} has different values. Aborting.", file=sys.stderr)
        sys.exit(1)
n_bins = data["n_bins"].iloc[0]
n_rays = data["n_rays"].iloc[0]
bin_res = data["bin_res"].iloc[0]



heights = alt/1000. + np.linspace(bin_res/2, (n_bins-1/2)*bin_res, n_bins)



for date in data["date"].drop_duplicates():
    data_by_date = data[data["date"]==date]
    
    # Skip date if missing Z or Zdr
    z = data_by_date[data_by_date["moment"]=="dBZ"]
    zdr = data_by_date[data_by_date["moment"]=="ZDR"]
    if z.empty or zdr.empty:
        print("Missing Z or Zdr.")
        continue
    
    z = z.iloc[0]
    zdr = zdr.iloc[0]
    
    # Remove no-data points
    mask = z["nodata_mask"] | zdr["nodata_mask"]

    # Keep points that are rain (RhoHV >= RHOHV_THRESHOLD, if available)
    rhohv = data_by_date[data_by_date["moment"]=="RhoHV"]
    if not rhohv.empty:
        rhohv = rhohv.iloc[0]
        mask = mask | (rhohv["data"]<RHOHV_THRESHOLD)

    # Stay in light rain
    mask = mask | (z["data"]<MIN_Z) | (z["data"]>MAX_Z)

    z["data"][mask] = None
    zdr["data"][mask] = None
    


# Concatenate all dates for Zdr
z_to_concat = data[data["moment"]=="dBZ"].sort_values(["date"])["data"]
zdr_to_concat = data[data["moment"]=="ZDR"].sort_values(["date"])["data"]
if not z_to_concat.empty:
    z_concat = np.stack(z_to_concat, axis=2)
    zdr_concat = np.stack(zdr_to_concat, axis=2)
else:
    z_concat = None
    zdr_concat = None



# Reduce to [min_height ; max_height]
valid_heights_indices = (MIN_H<=heights) & (heights<=MAX_H)
if z_concat is not None:
    z_concat = z_concat[:, valid_heights_indices, :]
    zdr_concat = zdr_concat[:, valid_heights_indices, :]
heights = heights[valid_heights_indices]



# Compute statistics
n_dates_effective = z_concat.shape[2]

# Zdr - Z distribution
bounds = list(range(MIN_Z, MAX_Z+2, 2))
mean_z = [bound + 1 for bound in bounds[:-1]]
z_zdr = pd.DataFrame(data={"dBZ":z_concat.flatten(), "ZDR":zdr_concat.flatten()}).dropna(subset="dBZ")
z_zdr["dBZ_groups"] = pd.cut(z_zdr["dBZ"], bins=bounds, include_lowest=True)
z_zdr_group_by_z = z_zdr.groupby("dBZ_groups", observed=False)
mean = z_zdr_group_by_z.mean()["ZDR"]
median = z_zdr_group_by_z.median()["ZDR"]
number_points = z_zdr_group_by_z.count()["ZDR"]

# Total Zdr ditribution
flat_zdr = zdr_concat.flatten()
mean_zdr_total = np.nanmean(flat_zdr)
median_zdr_total = np.nanmedian(flat_zdr)
std_zdr_total = np.nanstd(flat_zdr)

# By-azimut Zdr distribution
by_azimut_zdr = np.reshape(zdr_concat, (n_rays, -1))
mean_zdr_azimut = np.nanmean(by_azimut_zdr, axis=1)
median_zdr_azimut = np.nanmedian(by_azimut_zdr, axis=1)
std_zdr_azimut = np.nanstd(by_azimut_zdr, axis=1)
n_points_azimut = np.count_nonzero(~np.isnan(by_azimut_zdr), axis=1)

# By-distance Zdr distribution
by_distance_zdr = np.reshape(np.transpose(zdr_concat, (2, 0, 1)), (-1, len(heights)))
# Warning because tries to do the mean on full-nan values (for all the azimuts of a same distance), which is normal
mean_zdr_distance = np.nanmean(by_distance_zdr, axis=0)
median_zdr_distance = np.nanmedian(by_distance_zdr, axis=0)
std_zdr_distance = np.nanstd(by_distance_zdr, axis=0)
n_points_distance = np.count_nonzero(~np.isnan(by_distance_zdr), axis=0)



# Make plots
fig = plt.figure(figsize=(30, 20))
axs = fig.subplots(2, 2)

axs[0, 0].hist(flat_zdr, bins=100)
axs[0, 0].axvline(x=mean_zdr_total, color="r", ls="--", label="Mean")
axs[0, 0].axvline(x=median_zdr_total, color="tab:pink", ls="--", label="Median")
axs[0, 0].text(0.01, 0.85, f"Mean : {mean_zdr_total:.5f}\nMedian : {median_zdr_total:.5f}\nStandard deviation : {std_zdr_total:.5f}\nNumber of points : {len(flat_zdr)}", transform=axs[0,0].transAxes)
axs[0, 0].set_title("Total Zdr distribution")
axs[0, 0].legend(loc="upper right")
axs[0, 0].set_xlim([-10, 10])
axs[0, 0].set_ylabel("Number of points")

axs[0, 1].plot(mean_z, mean, label="Mean")
axs[0, 1].plot(mean_z, median, label="Median")
axs[0, 1].legend(loc="upper right")
axs[0, 1].set_xlabel("Z (dBZ)")
axs[0, 1].set_ylabel("Zdr (dB)")
axs[0, 1].set_xlim([MIN_Z, MAX_Z])
axs[0, 1].set_ylim([-3, 3])
axs[0, 1].set_title("Z-Zdr distribution")

ax_0_1_n_points = axs[0, 1].twinx()
ax_0_1_n_points.bar(mean_z, number_points, alpha=0.2, width=1)
ax_0_1_n_points.set_ylabel("Number of points")
ax_0_1_n_points.set_ylim([0, 100000])

axs[1, 0].plot(mean_zdr_azimut, label="Mean")
axs[1, 0].plot(median_zdr_azimut, label="Median")
axs[1, 0].plot(std_zdr_azimut, label="Standard deviation")
axs[1, 0].set_title("Zdr distribution by azimut")
axs[1, 0].legend(loc="upper right")
axs[1, 0].set_ylim([-3, 3])
axs[1, 0].set_xlabel("Azimut (deg)")
axs[1, 0].set_ylabel("Zdr (dB)")

ax_1_0_n_points = axs[1, 0].twinx()
ax_1_0_n_points.bar(np.linspace(0, 360, n_rays), n_points_azimut, alpha=0.2, width=1)
ax_1_0_n_points.set_ylabel("Number of points")
ax_1_0_n_points.set_ylim([0, n_bins*n_dates_effective])

axs[1, 1].plot(heights, mean_zdr_distance, label="Mean")
axs[1, 1].plot(heights, median_zdr_distance, label="Median")
axs[1, 1].plot(heights, std_zdr_distance, label="Standard deviation")
axs[1, 1].set_title("Zdr distribution by distance")
axs[1, 1].legend(loc="upper right")
axs[1, 1].set_ylim([-3, 3])
axs[1, 1].set_xlabel("Distance (km)")
axs[1, 1].set_ylabel("Zdr (dB)")

ax_1_1_n_points = axs[1, 1].twinx()
ax_1_1_n_points.bar(heights, n_points_distance, alpha=0.2, width=bin_res)
ax_1_1_n_points.set_ylabel("Number of points")
ax_1_1_n_points.set_ylim([0, n_rays*n_dates_effective])

fig.subplots_adjust(0.03, 0.03, 0.97, 0.9, 0.15, 0.15)
fig.suptitle(f"Zdr statistics for {radar.capitalize()} radar\nFrom {datetime.strptime(date_start, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M')} to {datetime.strptime(date_end, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M')}\nHeight range {MIN_H:.1f} km to {MAX_H:.1f} km")

print(f"Figure saved in {fig_file_name}")
fig.savefig(fig_file_name, dpi=100)
