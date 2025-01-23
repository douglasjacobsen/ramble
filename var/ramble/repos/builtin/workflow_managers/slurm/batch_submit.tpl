#!/bin/bash
sbatch {slurm_experiment_sbatch} | tee >(awk '{print $NF}' > {experiment_run_dir}/.slurm_job)
