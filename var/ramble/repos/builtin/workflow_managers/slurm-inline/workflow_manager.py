# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.wmkit import *

from ramble.wm.builtin.slurm import Slurm as SlurmBase


class SlurmInline(SlurmBase):
    """Inlined Slurm workflow manager

    This workflow managed performance the `{command}` steps inside of the
    `srun` command. This allows containerized experiments to perform their
    steps (such as exporting environment variables) inside the container
    instead of having to map external values into the container.

    Given this, the `mpi_command` definition ends up acting with the internal
    MPI to the container rather than an external MPI.
    """

    name = "slurm-inline"

    maintainers("douglasjacobsen")

    tags("workflow", "slurm")

    def __init__(self, file_path):
        super().__init__(file_path)

        self.runner = SlurmRunner()

    workflow_manager_variable(
        "workflow_banner",
        default="""# ****************************************************
# * Workflow manager: slurm-inline
# * Execution script is: {slurm_experiment_sbatch}
# * If this file is not the same as the above path, it is unlikely that this script
# * is used when `ramble on` executes experiments.
# ****************************************************
""",
        description="Banner to describe the workflow within execution templates",
    )

    formatted_executable(
        "slurm_inline_command",
        prefix="",
        indentation="4",
        join_separator="\n",
        commands=["{unformatted_command}"],
    )

    formatted_executable(
        "slurm_inline_command_without_logs",
        prefix="",
        indentation="4",
        join_separator="\n",
        commands=["{unformatted_command_without_logs}"],
    )

    register_template(
        name="slurm_experiment_sbatch",
        src_path="{slurm_execute_template_path}",
    )
