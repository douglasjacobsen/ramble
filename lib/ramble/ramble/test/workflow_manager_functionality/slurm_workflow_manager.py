# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)


def test_slurm_workflow():
    workspace_name = "test_slurm_workflow"

    test_config = """
ramble:
  variants:
    workflow_manager: '{wm_name}'
  variables:
    batch_submit: sbatch {execute_experiment}
    mpi_command: mpirun -n {n_ranks} -hostfile hostfile
    processes_per_node: 1
    n_nodes: 1
    wm_name: ['None', 'slurm']
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test_{wm_name}:
              variables:
                extra_sbatch_headers: |
                  #SBATCH --gpus-per-task={n_threads}
                  #SBATCH --time={time_limit_not_exist}
            test_{wm_name}_2:
              variables:
                slurm_partition: h3
            test_{wm_name}_3:
              variables:
                slurm_execute_template_path: $workspace_configs/execute_experiment.tpl
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()
        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)
        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()
        workspace("setup", "--dry-run", global_args=["-D", ws.root])

        # Assert on the all_experiments script
        all_exec_file = os.path.join(ws.root, "all_experiments")
        with open(all_exec_file) as f:
            content = f.read()
            batch_submit_path = os.path.join(
                ws.experiment_dir, "hostname", "local", "test_slurm", "batch_submit"
            )
            assert batch_submit_path in content
            # The sbatch is embedded in the batch_submit_path script instead
            assert f"sbatch {batch_submit_path}" not in content

        # Assert on no workflow manager
        path = os.path.join(ws.experiment_dir, "hostname", "local", "test_None")
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        assert "slurm_experiment_sbatch" not in files
        assert "batch_submit" not in files
        assert "batch_query" not in files
        assert "batch_cancel" not in files
        assert "batch_wait" not in files

        # Assert on slurm workflow manager
        path = os.path.join(ws.experiment_dir, "hostname", "local", "test_slurm")
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        assert "batch_submit" in files
        assert "batch_query" in files
        assert "batch_cancel" in files
        assert "batch_wait" in files
        with open(os.path.join(path, "batch_submit")) as f:
            content = f.read()
            # Assert the user-defined `batch_submit` is included
            assert "slurm_experiment_sbatch" not in content
            assert "execute_experiment" in content
            assert ".slurm_job" in content
            assert "sbatch" in content
        with open(os.path.join(path, "slurm_experiment_sbatch")) as f:
            content = f.read()
            assert "scontrol show hostnames" in content
            assert "#SBATCH --gpus-per-task=1" in content
            assert "#SBATCH -p" not in content
            assert "#SBATCH --time" not in content
        with open(os.path.join(path, "batch_query")) as f:
            content = f.read()
            assert "squeue" in content
        with open(os.path.join(path, "batch_cancel")) as f:
            content = f.read()
            assert "scancel" in content

        # Assert on the experiment with non-empty partition variable given
        path = os.path.join(ws.experiment_dir, "hostname", "local", "test_slurm_2")
        with open(os.path.join(path, "slurm_experiment_sbatch")) as f:
            content = f.read()
            assert "#SBATCH -p h3" in content

        # Assert on the experiment with custom slurm execute template
        path = os.path.join(ws.experiment_dir, "hostname", "local", "test_slurm_3")
        assert not os.path.exists(os.path.join(path, "slurm_experiment_sbatch"))
        with open(os.path.join(path, "execute_experiment")) as f:
            content = f.read()
            # Since it uses the default execute_experiment tpl, no slurm content is present
            assert "#SBATCH" not in content
            assert "scontrol" not in content
