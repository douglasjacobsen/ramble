# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.wmkit import *
from ramble.expander import ExpanderError
from ramble.application import experiment_status

from spack.util.executable import ProcessError

# Mapping from squeue/sacct status to Ramble status
_STATUS_MAP = {
    "PD": "SUBMITTED",
    "R": "RUNNING",
    "CF": "SETUP",
    "CG": "COMPLETE",
    "COMPLETED": "COMPLETE",
    "CANCELLED": "CANCELLED",
    "CANCELLED+": "CANCELLED",
}


def _declare_status_map():
    """A utility to convert the `_STATUS_MAP` into a bash array"""
    entries = ["declare -A status_map"]
    for k, v in _STATUS_MAP.items():
        entries.append(f'status_map["{k}"]="{v}"')
    return "\n".join(entries)


class Slurm(WorkflowManagerBase):
    """Slurm workflow manager"""

    name = "slurm"

    maintainers("linsword13")

    tags("workflow", "slurm")

    def __init__(self, file_path):
        super().__init__(file_path)

        self.runner = SlurmRunner()

    workflow_manager_variable(
        name="job_name",
        default="{application_name}_{workload_name}_{experiment_name}",
        description="Slurm job name",
    )

    workflow_manager_variable(
        name="extra_sbatch_headers",
        default="",
        description="Extra sbatch headers added to slurm job script",
    )

    workflow_manager_variable(
        name="hostlist",
        default="$SLURM_JOB_NODELIST",
        description="hostlist variable used by various modifiers",
    )

    workflow_manager_variable(
        name="srun_args",
        default="-n {n_ranks}",
        description="Arguments supplied to srun",
    )

    workflow_manager_variable(
        name="mpi_command",
        default="srun {srun_args}",
        description="mpirun prefix, mostly served as an overridable default",
    )

    register_template(
        name="batch_submit",
        src_name="batch_submit.tpl",
        dest_path="batch_submit",
    )

    register_template(
        name="batch_query",
        src_name="batch_query.tpl",
        dest_path="batch_query",
        extra_vars={"declare_status_map": _declare_status_map()},
    )

    register_template(
        name="batch_cancel",
        src_name="batch_cancel.tpl",
        dest_path="batch_cancel",
    )

    register_template(
        name="slurm_execute_experiment",
        src_name="slurm_execute_experiment.tpl",
        dest_path="slurm_execute_experiment",
        extra_vars_func="execute_vars",
    )

    def _execute_vars(self):
        expander = self.app_inst.expander
        # Adding pre-defined and custom headers
        pragmas = [
            ("#SBATCH -N {n_nodes}"),
            ("#SBATCH -p {partition}"),
            ("#SBATCH --ntasks-per-node {processes_per_node}"),
            ("#SBATCH -J {job_name}"),
            ("#SBATCH -o {experiment_run_dir}/slurm-%j.out"),
            ("#SBATCH -e {experiment_run_dir}/slurm-%j.err"),
            ("#SBATCH --gpus-per-node {gpus_per_node}"),
        ]
        try:
            extra_sbatch_headers_raw = expander.expand_var_name(
                "extra_sbatch_headers", allow_passthrough=False
            )
            extra_sbatch_headers = extra_sbatch_headers_raw.strip().split("\n")
            pragmas = pragmas + extra_sbatch_headers
        except ExpanderError:
            pass
        header_str = "\n".join(self.conditional_expand(pragmas))
        return {"sbatch_headers_str": header_str}

    def get_status(self, workspace):
        expander = self.app_inst.expander
        run_dir = expander.expand_var_name("experiment_run_dir")
        job_id_file = os.path.join(run_dir, ".slurm_job")
        status = experiment_status.UNKNOWN
        if not os.path.isfile(job_id_file):
            logger.warn("job_id file is missing")
            return status
        with open(job_id_file) as f:
            job_id = f.read().strip()
        self.runner.set_dry_run(workspace.dry_run)
        wm_status_raw = self.runner.get_status(job_id)
        wm_status = _STATUS_MAP.get(wm_status_raw)
        if wm_status is not None and hasattr(experiment_status, wm_status):
            status = getattr(experiment_status, wm_status)
        return status


class SlurmRunner:
    """Runner for executing slurm commands"""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.squeue_runner = None
        self.sacct_runner = None
        self.run_dir = None

    def _ensure_runner(self, runner_name: str):
        attr = f"{runner_name}_runner"
        if getattr(self, attr) is None:
            setattr(
                self,
                attr,
                CommandRunner(name=runner_name, command=runner_name),
            )

    def set_dry_run(self, dry_run=False):
        """
        Set the dry_run state of this runner
        """
        self.dry_run = dry_run

    def get_status(self, job_id):
        if self.dry_run:
            return None
        self._ensure_runner("squeue")
        squeue_args = ["-h", "-o", "%t", "-j", job_id]
        try:
            status_out = self.squeue_runner.command(
                *squeue_args, output=str, error=os.devnull
            )
        except ProcessError as e:
            status_out = ""
            logger.debug(
                f"squeue returns error {e}. This is normal if the job has already been completed."
            )
        if not status_out:
            self._ensure_runner("sacct")
            sacct_args = ["-o", "state", "-X", "-n", "-j", job_id]
            status_out = self.sacct_runner.command(*sacct_args, output=str)
        return status_out.strip()
