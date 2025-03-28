#!/bin/bash

# Ensure job_id is present
job_id=$(< {experiment_run_dir}/.slurm_job)
if [ -z "${job_id:-}" ]; then
    echo "No valid job_id found" 1>&2
    exit 1
fi

echo "Waiting for job {job_name} with id ${job_id} to complete..."

while true; do
    status=$(squeue -h -o "%t" -j "${job_id}" 2>/dev/null)
    # The absence of the job from squeue indicates it's completed.
    if [ -z "$status" ]; then
        break
    else
        sleep 10
    fi
done

echo "job {job_name} with id ${job_id} is done"
