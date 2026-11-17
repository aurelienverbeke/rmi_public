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



min_availability=0.95



##########
# Daily shift
##########
logdir="/logs/ds/${begin_date}-${end_date}"
mkdir -p "$logdir"



##### RR

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date rainbow_single_rr hic_5m $min_availability -r1 $radar > "$logdir/rainbow_single_rr_hic_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date rainbow_single_rr spw_5m $min_availability -r1 $radar > "$logdir/rainbow_single_rr_spw_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date rainbow_single_rr vmm_5m $min_availability -r1 $radar > "$logdir/rainbow_single_rr_vmm_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_single_rr hic_5m $min_availability -r1 $radar > "$logdir/radqpe2_single_rr_hic_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_single_rr spw_5m $min_availability -r1 $radar > "$logdir/radqpe2_single_rr_spw_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_single_rr vmm_5m $min_availability -r1 $radar > "$logdir/radqpe2_single_rr_vmm_5m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_edk_5m hic_5m $min_availability > "$logdir/radqpe2_comp_edk_5m_hic_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_mfb_5m hic_5m $min_availability > "$logdir/radqpe2_comp_mfb_5m_hic_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_edk_5m spw_5m $min_availability > "$logdir/radqpe2_comp_edk_5m_spw_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_mfb_5m spw_5m $min_availability > "$logdir/radqpe2_comp_mfb_5m_spw_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_edk_5m vmm_5m $min_availability > "$logdir/radqpe2_comp_edk_5m_vmm_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_mfb_5m vmm_5m $min_availability > "$logdir/radqpe2_comp_mfb_5m_vmm_5m" 2>&1



##### 5M

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_single_5m hic_5m $min_availability -r1 $radar > "$logdir/radqpe2_single_5m_hic_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_single_5m spw_5m $min_availability -r1 $radar > "$logdir/radqpe2_single_5m_spw_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_single_5m vmm_5m $min_availability -r1 $radar > "$logdir/radqpe2_single_5m_vmm_5m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_edk_5m hic_5m $min_availability > "$logdir/radqpe2_comp_edk_5m_hic_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_mfb_5m hic_5m $min_availability > "$logdir/radqpe2_comp_mfb_5m_hic_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_edk_5m spw_5m $min_availability > "$logdir/radqpe2_comp_edk_5m_spw_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_mfb_5m spw_5m $min_availability > "$logdir/radqpe2_comp_mfb_5m_spw_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_edk_5m vmm_5m $min_availability > "$logdir/radqpe2_comp_edk_5m_vmm_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic ds $begin_date $end_date radqpe2_comp_mfb_5m vmm_5m $min_availability > "$logdir/radqpe2_comp_mfb_5m_vmm_5m" 2>&1



wait # We need all the gauge shifts to compute the mean one
echo "All jobs completed. Logs available in $logdir/"



##########
# Daily mean shift
# Force max. 5 processes otherwise there are too many processes trying to access the database
##########
logdir="/logs/dms/${begin_date}-${end_date}"
mkdir -p "$logdir"
if [[ $max_jobs -ge 5 ]]
then
    max_jobs=5
fi



##### RR

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic dms $begin_date $end_date rainbow_single_rr hic_5m $min_availability -r1 $radar -g spw_5m -g vmm_5m > "$logdir/rainbow_single_rr_hic_spw_vmm_5m_${radar}" 2>&1
    run_job python3 -m viscalmon.qpe_qc.qc_periodic dms $begin_date $end_date radqpe2_single_rr hic_5m $min_availability -r1 $radar -g spw_5m -g vmm_5m > "$logdir/radqpe2_single_rr_hic_spw_vmm_5m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic dms $begin_date $end_date radqpe2_comp_edk_5m hic_5m $min_availability -g spw_5m -g vmm_5m > "$logdir/radqpe2_comp_edk_5m_hic_spw_vmm_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic dms $begin_date $end_date radqpe2_comp_mfb_5m hic_5m $min_availability -g spw_5m -g vmm_5m > "$logdir/radqpe2_comp_mfb_5m_hic_spw_vmm_5m" 2>&1



##### 5M

# single vs gauge
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic dms $begin_date $end_date radqpe2_single_5m hic_5m $min_availability -r1 $radar -g spw_5m -g vmm_5m > "$logdir/radqpe2_single_5m_hic_spw_vmm_5m_${radar}" 2>&1
done

# comp vs gauge
run_job python3 -m viscalmon.qpe_qc.qc_periodic dms $begin_date $end_date radqpe2_comp_edk_5m hic_5m $min_availability -g spw_5m -g vmm_5m > "$logdir/radqpe2_comp_edk_5m_hic_spw_vmm_5m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic dms $begin_date $end_date radqpe2_comp_mfb_5m hic_5m $min_availability -g spw_5m -g vmm_5m > "$logdir/radqpe2_comp_mfb_5m_hic_spw_vmm_5m" 2>&1



wait
echo "All jobs completed. Logs available in $logdir/"