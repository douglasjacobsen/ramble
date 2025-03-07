#!/bin/bash

. {batch_helpers}

job_id=$(get_job_id)

scancel ${job_id}
