#!/bin/bash

# ----------------------------------------------------------------------------------------------------
# CONSTANTS
# DO NOT CHANGE
# ----------------------------------------------------------------------------------------------------
# Catch Ctrl-C and close all
trap cleanup SIGINT

cleanup() {
	kill ${pids_to_wait[*]} 2>/dev/null
	wait ${pids_to_wait[*]} 2>/dev/null
	rm -f "$tmp_vertical" "$tmp_volume" "$tmp_composite"
	exit 1
}
# ----------------------------------------------------------------------------------------------------





# ----------------------------------------------------------------------------------------------------
# ALL PERIODS TO COMPUTE
# ----------------------------------------------------------------------------------------------------
#radar		date_start		date_end
toRun=(
#jabbeke		202505240750		202505240915
jabbeke		202505271225		202505271615
#jabbeke		202506051955		202506052125
#jabbeke		202506070240		202506070325
#jabbeke		202506132315		202506140020
#jabbeke		202506252215		202506260105
#jabbeke		202506270355		202506270425
#jabbeke		202507060710		202507060955
#jabbeke		202507201100		202507201235
#wideumont	202505272310		202505280055
#wideumont	202506051820		202506052350
#wideumont	202506141035		202506141220
#wideumont	202506150030		202506150200
#wideumont	202506260055		202506260145
#wideumont	202506261000		202506261130
#wideumont	202506270545		202506270625
wideumont	202507060525		202507061025
#wideumont	202507160555		202507160630	# for tests after Wideumont calibration campaign, not a perfect situation
#wideumont	202507201240		202507201335
)
N_COLUMNS=3
# ----------------------------------------------------------------------------------------------------





# ----------------------------------------------------------------------------------------------------
# RUN ALL STATISTICS
# DO NOT CHANGE
# ----------------------------------------------------------------------------------------------------
mkdir -p $DIR_ZDR_VERTICAL
mkdir -p $DIR_ZDR_CONSISTENCY
mkdir -p $DIR_Z_CONSISTENCY
mkdir -p $DIR_COMPOSITE
for((i=0; i < ${#toRun[@]}; i+=N_COLUMNS))
do
	# Make the terminal outputs more readable
	echo ""

	# Get all info from array above
	runInfo=( "${toRun[@]:i:N_COLUMNS}" )

	radar=${runInfo[0]}
	date_start=${runInfo[1]}
	date_end=${runInfo[2]}
	echo "Running : Radar $radar | Dates $date_start - $date_end"
	


	# Verify dates format and radar name
	if [[ ! ($date_start =~ ^[0-9]{12}$) || ! ($date_end =~ ^[0-9]{12}$) ]]; then
		echo "Wrong date format : YYYYMMDDHHMM."
		exit 1
	fi

	if [[ $radar != "jabbeke" && $radar != "wideumont" ]]; then
		echo "Wrong radar name. Please choose either jabbeke or wideumont."
		exit 1
	fi



	# Verify end date is after start date
	if [[ $date_start -gt $date_end ]]; then
		echo "Start date is after end date."
		exit 1
	fi



	# All days between the two dates, to browse folders
	dates_days=()
	current=${date_start:0:8}
	end=${date_end:0:8}
	while [[ "$current" -le "$end" ]]; do
		dates_days+=("$current")
		current=$(date -d "$current +1 day" +%Y%m%d)
	done



	# Retrieve file names for each date between start and end dates

	tmp_vertical=$(mktemp)
	tmp_volume=$(mktemp)
	tmp_composite=$(mktemp)



	pids_to_wait=()
	for date in ${dates_days[*]}; do
		{
			data_dir_vertical="/mnt/HDS_ERS/archive/${date:0:4}/${date:4:2}/${date:6:2}/radar/single/$radar/azi/"

			if [[ ! -d "$data_dir_vertical" ]]; then
				echo "Data directory not found: $data_dir_vertical"
				exit 1
			fi

			for file in $(find "$data_dir_vertical" -type f \( \
				-name "*ZDR.azi" \
				-o -name "*RhoHV.azi" \
				-o -name "*dBZ.azi" \
			\)); do
				filename=$(basename "$file")
				date_file="${filename:0:12}"

				if [[ "$date_file" -ge "$date_start" && "$date_file" -le "$date_end" ]]; then
					echo "$file" >> "$tmp_vertical"
				fi
			done
		} &
		pids_to_wait+=($!)



		{
			data_dir_volume="/mnt/HDS_ERS/archive/${date:0:4}/${date:4:2}/${date:6:2}/radar/single/$radar/vol/be${radar:0:3}_scan_v3_Z/bin/"

			if [[ ! -d "$data_dir_volume" ]]; then
				echo "Data directory not found: $data_dir_volume"
				exit 1
			fi

			for file in $(find "$data_dir_volume" -type f \( \
				-name "????????????????dBZ.vol" \
				-o -name "????????????????ZDR.vol" \
				-o -name "????????????????RhoHV.vol" \
				-o -name "????????????????uPhiDP.vol" \
				-o -name "????????????????PhiDP.vol" \
			\)); do
				filename=$(basename "$file")
				date_file="${filename:0:12}"

				if [[ "$date_file" -ge "$date_start" && "$date_file" -le "$date_end" ]]; then
					echo "$file" >> "$tmp_volume"
				fi
			done
		}&
		pids_to_wait+=($!)



		{
			data_dir_composite="/mnt/HDS_ERS/archive/${date:0:4}/${date:4:2}/${date:6:2}/radar/composite/belradcomp/sri/beborder00/png/"

			if [[ ! -d "$data_dir_composite" ]]; then
				echo "Data directory not found: $data_dir_composite"
				exit 1
			fi

			for file in "$data_dir_composite"*; do
				filename=$(basename "$file")
				date_file="${filename:0:12}"

				if [[ "$date_file" -ge "$date_start" && "$date_file" -le "$date_end" ]]; then
					echo "$file" >> "$tmp_composite"
				fi
			done
		} &
		pids_to_wait+=($!)
	done
	
	wait ${pids_to_wait[*]}

	vertical_files=($(cat "$tmp_vertical"))
	volume_files=($(cat "$tmp_volume"))
	composite_rainfall_files=($(cat "$tmp_composite"))

	rm -f "$tmp_vertical" "$tmp_volume" "$tmp_composite"



	# Run python : statistics and plots
	# All together
	
	pids_to_wait=()

	echo "Running python script zdr_vertical"
	(python3 -m viscalmon.calibration.zdr_vertical $radar $date_start $date_end ${vertical_files[*]} > >(sed 's/^/Python(ZDR_Vertical)> /') 2> >(sed 's/^/Python(ZDR_Vertical:ERR)> /' >&2)) &
	pids_to_wait+=($!)
	echo "Running python script zdr_consistency"
	(python3 viscalmon.calibration.zdr_consistency $radar $date_start $date_end ${volume_files[*]} > >(sed 's/^/Python(ZDR_Consistency)> /') 2> >(sed 's/^/Python(ZDR_Consistency:ERR)> /' >&2)) &
	pids_to_wait+=($!)
	echo "Running python script z_consistency"
	(python3 viscalmon.calibration.z_consistency $radar $date_start $date_end ${volume_files[*]} > >(sed 's/^/Python(Z_Consistency)> /') 2> >(sed 's/^/Python(Z_Consistency:ERR)> /' >&2)) &
	pids_to_wait+=($!)

	echo "Saving rainfall composite at mid-interval"
	nb_files=${#composite_rainfall_files[@]}
	median_index=$((nb_files/2))
	cp -f "${composite_rainfall_files[$median_index]}" "${DIR_COMPOSITE}${date_start}-${date_end}.png" &

	wait ${pids_to_wait[*]}
done
# ----------------------------------------------------------------------------------------------------
