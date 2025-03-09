#!/bin/bash

. {batch_helpers}

job_id=$(get_job_id)

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

# Print also the nodelist, start and end times of the job
echo "additional job info:"
paste -d ":" \
  <(echo "nodes start end" | xargs -n1) \
  <(sacct -j "${job_id}" -o 'nodelist%80,start,end' -X -n | xargs -n1) \
  | sed "s/^/  /"
