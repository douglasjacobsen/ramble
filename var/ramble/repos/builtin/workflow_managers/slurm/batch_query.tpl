#!/bin/bash

# Ensure job_id is present
job_id=$(< {experiment_run_dir}/.slurm_job)
if [ -z "${job_id:-}" ]; then
    echo "No valid job_id found" 1>&2
    exit 1
fi

# Set up the status_map mapping between
# sacct/squeue status to ramble counterpart
{declare_status_map}

status=$(squeue -h -o "%t" -j "${job_id}" 2>/dev/null)
if [ -z "$status" ]; then
    status=$(sacct -j "${job_id}" -o state -X -n | xargs)
fi
if [ ! -z "$status" ]; then
    if [ -v status_map["$status"] ]; then
        status=${status_map["$status"]}
    fi
fi
echo "job {job_name} with id ${job_id} has status: $status"
