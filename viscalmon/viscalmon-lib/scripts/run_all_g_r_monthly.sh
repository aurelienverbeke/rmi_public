#!/bin/bash



# ----------------------------------------------------------------------------------------------------
# CLEANUP FUNCTION
# ----------------------------------------------------------------------------------------------------
# Catch Ctrl-C and close all
trap cleanup SIGINT

cleanup() {
	kill -- -$$ 2>/dev/null
    wait 2>/dev/null
    exit 1
}
# ----------------------------------------------------------------------------------------------------



# ----------------------------------------------------------------------------------------------------
# INPUTS
#
# begin date
# end date
# max jobs concurrently
# ----------------------------------------------------------------------------------------------------
begin_date=$1
end_date=$2
max_jobs=${3:-5}
# ----------------------------------------------------------------------------------------------------



# ----------------------------------------------------------------------------------------------------
# PARALLEL MANAGER
# ----------------------------------------------------------------------------------------------------
running=0

run_job() {
    "$@" &
    ((running++))

    if (( running >= max_jobs )); then
        wait -n
        ((running--))
    fi
}
# ----------------------------------------------------------------------------------------------------



min_rates="-p 0.2 -p 1 -p 5"
min_availability=0.8



##########
# Per gauge
##########
logdir="/logs/mgr/${begin_date}-${end_date}"
mkdir -p "$logdir"



##### 5M

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_single_5m hic_5m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_5m_hic_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_single_5m spw_5m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_5m_spw_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_single_5m vmm_5m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_5m_vmm_5m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_edk_5m hic_5m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_5m_hic_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_mfb_5m hic_5m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_5m_hic_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_edk_5m spw_5m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_5m_spw_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_mfb_5m spw_5m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_5m_spw_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_edk_5m vmm_5m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_5m_vmm_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_mfb_5m vmm_5m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_5m_vmm_5m" 2>&1



##### 10M

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_single_10m aws_10m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_10m_aws_10m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date rainbow_comp_10m aws_10m $min_availability $min_rates > "$logdir/rainbow_comp_10m_aws_10m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_edk_10m aws_10m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_10m_aws_10m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_mfb_10m aws_10m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_10m_aws_10m" 2>&1



##### 1H

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date rainbow_single_1h aws_10m $min_availability -r1 $radar $min_rates > "$logdir/rainbow_single_1h_aws_10m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_single_1h aws_10m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_1h_aws_10m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date rainbow_comp_1h aws_10m $min_availability $min_rates > "$logdir/rainbow_comp_1h_aws_10m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_edk_1h aws_10m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_1h_aws_10m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_mfb_1h aws_10m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_1h_aws_10m" 2>&1



##### 1D

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date rainbow_single_1d obs_1d $min_availability -r1 $radar $min_rates > "$logdir/rainbow_single_1d_obs_1d_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_single_1d aws_10m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_1d_aws_10m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_single_mfb_1d aws_10m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_mfb_1d_aws_10m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_edk_1d obs_1d $min_availability $min_rates > "$logdir/radqpe2_comp_edk_1d_obs_1d" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mgr $begin_date $end_date radqpe2_comp_mfb_1d obs_1d $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_1d_obs_1d" 2>&1



wait # We need all the gauge statistics to compute the mean one
echo "All jobs completed. Logs available in $logdir/"



##########
# Mean
# Force max. 5 processes otherwise there are too many processes trying to access the database
##########
logdir="/logs/mmgr/${begin_date}-${end_date}"
mkdir -p "$logdir"
if [[ $max_jobs -ge 5 ]]
then
    max_jobs=5
fi



##### 5M

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_single_5m hic_5m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_5m_hic_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_single_5m spw_5m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_5m_spw_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_single_5m vmm_5m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_5m_vmm_5m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_edk_5m hic_5m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_5m_hic_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_mfb_5m hic_5m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_5m_hic_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_edk_5m spw_5m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_5m_spw_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_mfb_5m spw_5m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_5m_spw_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_edk_5m vmm_5m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_5m_vmm_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_mfb_5m vmm_5m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_5m_vmm_5m" 2>&1



##### 10M

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_single_10m aws_10m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_10m_aws_10m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date rainbow_comp_10m aws_10m $min_availability $min_rates > "$logdir/rainbow_comp_10m_aws_10m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_edk_10m aws_10m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_10m_aws_10m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_mfb_10m aws_10m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_10m_aws_10m" 2>&1



##### 1H

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date rainbow_single_1h aws_10m $min_availability -r1 $radar $min_rates > "$logdir/rainbow_single_1h_aws_10m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_single_1h aws_10m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_1h_aws_10m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date rainbow_comp_1h aws_10m $min_availability $min_rates > "$logdir/rainbow_comp_1h_aws_10m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_edk_1h aws_10m $min_availability $min_rates > "$logdir/radqpe2_comp_edk_1h_aws_10m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_mfb_1h aws_10m $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_1h_aws_10m" 2>&1



##### 1D

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date rainbow_single_1d obs_1d $min_availability -r1 $radar $min_rates > "$logdir/rainbow_single_1d_obs_1d_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_single_1d aws_10m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_1d_aws_10m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_single_mfb_1d aws_10m $min_availability -r1 $radar $min_rates > "$logdir/radqpe2_single_mfb_1d_aws_10m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_edk_1d obs_1d $min_availability $min_rates > "$logdir/radqpe2_comp_edk_1d_obs_1d" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mmgr $begin_date $end_date radqpe2_comp_mfb_1d obs_1d $min_availability $min_rates > "$logdir/radqpe2_comp_mfb_1d_obs_1d" 2>&1



wait
echo "All jobs completed. Logs available in $logdir/"