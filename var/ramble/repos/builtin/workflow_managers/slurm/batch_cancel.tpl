#!/bin/bash

# Ensure job_id is present
job_id=$(< {experiment_run_dir}/.slurm_job)
if [ -z "${job_id:-}" ]; then
    echo "No valid job_id found" 1>&2
    exit 1
fi

scancel ${job_id}
