#!/bin/bash
{workflow_pragmas}

{workflow_banner}

cd {experiment_run_dir}

{workflow_hostfile_cmd}

read -r -d '' CMD <<- EOM
{slurm_inline_command_without_logs}
EOM

{mpi_command} $CMD
