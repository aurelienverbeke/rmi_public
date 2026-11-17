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
min_availability=0.95



logdir="/logs/mrr/${begin_date}-${end_date}"
mkdir -p "$logdir"



##### RR

# single vs single
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mrr $begin_date $end_date rainbow_single_rr radqpe2_single_rr $min_availability -r1 $radar -r2 $radar $min_rates > "$logdir/rainbow_single_rr_radqpe2_single_rr_${radar}" 2>&1
done

# comp vs comp
run_job python3 -m viscalmon.qpe_qc.qc_periodic mrr $begin_date $end_date rainbow_comp_be_rr radqpe2_comp_edk_rr $min_availability $min_rates > "$logdir/rainbow_comp_be_rr_radqpe2_comp_edk_rr" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mrr $begin_date $end_date rainbow_comp_be_rr radqpe2_comp_mfb_rr $min_availability $min_rates > "$logdir/rainbow_comp_be_rr_radqpe2_comp_mfb_rr" 2>&1



##### 10M

# comp vs comp
run_job python3 -m viscalmon.qpe_qc.qc_periodic mrr $begin_date $end_date rainbow_comp_10m radqpe2_comp_edk_10m $min_availability $min_rates > "$logdir/rainbow_comp_10m_radqpe2_comp_edk_10m" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mrr $begin_date $end_date rainbow_comp_10m radqpe2_comp_mfb_10m $min_availability $min_rates > "$logdir/rainbow_comp_10m_radqpe2_comp_mfb_10m" 2>&1



##### 1H

# single vs single
for radar in jabbeke wideumont avesnois helchteren; do
    run_job python3 -m viscalmon.qpe_qc.qc_periodic mrr $begin_date $end_date rainbow_single_1h radqpe2_single_1h $min_availability -r1 $radar -r2 $radar $min_rates > "$logdir/rainbow_single_1h_radqpe2_single_1h_${radar}" 2>&1
done

# comp vs comp
run_job python3 -m viscalmon.qpe_qc.qc_periodic mrr $begin_date $end_date rainbow_comp_1h radqpe2_comp_edk_1h $min_availability $min_rates > "$logdir/rainbow_comp_1h_radqpe2_comp_edk_1h" 2>&1
run_job python3 -m viscalmon.qpe_qc.qc_periodic mrr $begin_date $end_date rainbow_comp_1h radqpe2_comp_mfb_1h $min_availability $min_rates > "$logdir/rainbow_comp_1h_radqpe2_comp_mfb_1h" 2>&1



wait
echo "All jobs completed. Logs available in $logdir/"