# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.wmkit import *
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
    "FAILED": "FAILED",
    "TIMEOUT": "TIMEOUT",
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
        "workflow_banner",
        default="""# ****************************************************
# * Workflow manager: slurm
# * Execution script is: {slurm_experiment_sbatch}
# * If this file is not the same as the above path, it is unlikely that this script
# * is used when `ramble on` executes experiments.
# ****************************************************
""",
        description="Banner to describe the workflow within execution templates",
    )

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

    workflow_manager_variable(
        name="slurm_partition",
        default="",
        description="partition to submit job to, if unspecified, it uses the default partition",
    )

    workflow_manager_variable(
        name="workflow_node_id",
        default="${SLURM_NODEID}",
        description="node ID to be inserted at runtime",
    )

    workflow_manager_variable(
        name="slurm_execute_template_path",
        default="slurm_experiment_sbatch.tpl",
        description="Path to the custom template for generating the slurm sbatch job script. "
        "For a relative path, it is searched under the workflow manager's source directory. "
        "The path can contain workspace path variables such as $workspace_config.",
    )

    register_template(
        name="batch_submit",
        src_path="batch_submit.tpl",
        dest_path="batch_submit",
        extra_vars_func="batch_submit_vars",
    )

    def _batch_submit_vars(self):
        vars = self.app_inst.variables
        old_var_name = "_old_batch_submit"
        if old_var_name in vars:
            batch_submit_cmd = vars[old_var_name]
            if "sbatch" not in batch_submit_cmd:
                logger.warn(
                    "`sbatch` is missing in the given `batch_submit` command"
                )
        else:
            batch_submit_script = vars["slurm_experiment_sbatch"]
            batch_submit_cmd = f"sbatch {batch_submit_script}"
        return {
            "batch_submit_cmd": batch_submit_cmd,
        }

    register_template(
        name="batch_query",
        src_path="batch_query.tpl",
        dest_path="batch_query",
        extra_vars={"declare_status_map": _declare_status_map()},
    )

    register_template(
        name="batch_cancel",
        src_path="batch_cancel.tpl",
        dest_path="batch_cancel",
    )

    register_template(
        name="batch_wait",
        src_path="batch_wait.tpl",
        dest_path="batch_wait",
    )

    register_template(
        name="slurm_experiment_sbatch",
        src_path="{slurm_execute_template_path}",
    )

    def template_render_vars(self):
        vars = {}
        expander = self.app_inst.expander
        # Adding pre-defined and custom headers
        pragmas = [
            ("#SBATCH -N {n_nodes}"),
            ("#SBATCH --ntasks-per-node {processes_per_node}"),
            ("#SBATCH -J {job_name}"),
            ("#SBATCH -o {experiment_run_dir}/slurm-%j.out"),
            ("#SBATCH -e {experiment_run_dir}/slurm-%j.err"),
            ("#SBATCH --gpus-per-node {gpus_per_node}"),
        ]
        partition = expander.expand_var_name("slurm_partition")
        if partition:
            pragmas.append("#SBATCH -p {slurm_partition}")
        extra_headers = (
            self.app_inst.variables["extra_sbatch_headers"].strip().split("\n")
        )
        pragmas = pragmas + extra_headers
        header_str = "\n".join(self.conditional_expand(pragmas))
        return {
            **vars,
            "workflow_pragmas": header_str,
            "workflow_hostfile_cmd": self.runner.get_hostfile_cmd(),
        }

    def get_status(self, workspace):
        expander = self.app_inst.expander
        run_dir = expander.expand_var_name("experiment_run_dir")
        job_id_file = os.path.join(run_dir, ".slurm_job")
        status = experiment_status.UNRESOLVED
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
        if status == experiment_status.UNRESOLVED:
            logger.warn(
                f"The slurm workflow manager failed to resolve the status of job {job_id}. "
                "Enable debug mode (`ramble -d`) for more detailed error messages."
            )
        return status


class SlurmRunner:
    """Runner for executing slurm commands"""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.squeue_runner = None
        self.sacct_runner = None
        self.sinfo_runner = None
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
            try:
                status_out = self.sacct_runner.command(*sacct_args, output=str)
            except ProcessError as e:
                status_out = ""
                logger.debug(
                    f"sacct returns error {e}. The status is not resolved correctly."
                )
        return status_out.strip()

    def get_partitions(self):
        if self.dry_run:
            return None
        self._ensure_runner("sinfo")
        sinfo_args = ["-h"]
        out = self.sinfo_runner.command(*sinfo_args, output=str).strip()
        partitions = set()
        default_partition = None
        for line in out.split("\n"):
            info = line.split()
            name = info[0].strip()
            if name.endswith("*"):
                name = name[:-1]
                default_partition = name
            partitions.add(name)
        return {
            "default_partition": default_partition,
            "partitions": partitions,
        }

    def get_hostfile_cmd(self):
        return "scontrol show hostnames > {hostfile}"
