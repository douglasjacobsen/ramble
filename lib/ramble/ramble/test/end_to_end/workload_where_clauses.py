# Copyright 2022-2026 The Ramble Authors
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

# everything here should be mocked if possible
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_workload_where_clauses(
    mutable_config, mutable_mock_workspace_path, mutable_mock_apps_repo, capsys
):
    """Test workload where and exclude_where clauses."""

    test_config = """
ramble:
  variables:
    mpi_command: ''
    batch_submit: '{execute_experiment}'
    partition: '1'
    processes_per_node: '1'
    n_threads: '1'
  applications:
    workload-where-mock:
      workloads:
        always:
          experiments:
            test1:
              variables:
                test_var: 'foo'
        only_when_var_is_foo:
          experiments:
            test_foo:
              variables:
                test_var: 'foo'
            test_bar:
              variables:
                test_var: 'bar'
        exclude_when_var_is_bar:
          experiments:
            test_foo:
              variables:
                test_var: 'foo'
            test_bar:
              variables:
                test_var: 'bar'
"""
    workspace_name = "test_workload_where_clauses"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, "ramble.yaml")

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(test_config)

    ws._re_read()

    out = workspace("setup", "--dry-run", global_args=["-D", ws.root])

    # 'always' workload should generate test1
    assert "workload-where-mock.always.test1" in out

    # 'only_when_var_is_foo' workload should generate test_foo but drop test_bar
    assert "workload-where-mock.only_when_var_is_foo.test_foo" in out
    assert "workload-where-mock.only_when_var_is_foo.test_bar" not in out

    # 'exclude_when_var_is_bar' workload should generate test_foo but drop test_bar
    assert "workload-where-mock.exclude_when_var_is_bar.test_foo" in out
    assert "workload-where-mock.exclude_when_var_is_bar.test_bar" not in out


def test_workload_where_clauses_warnings(
    mutable_config, mutable_mock_workspace_path, mutable_mock_apps_repo
):
    """Test workload where and exclude_where clauses."""

    test_config = """
ramble:
  variables:
    mpi_command: ''
    batch_submit: '{execute_experiment}'
    partition: '1'
    processes_per_node: '1'
    n_threads: '1'
  applications:
    workload-where-mock:
      workloads:
        only_when_var_is_foo:
          experiments:
            test_bar:
              variables:
                test_var: 'bar'
            test_baz:
              variables:
                test_var: 'baz'
"""
    workspace_name = "test_workload_where_clauses_warnings"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, "ramble.yaml")

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(test_config)

    ws._re_read()

    out = workspace("setup", "--dry-run", global_args=["-D", ws.root])

    # All experiments for only_when_var_is_foo are dropped.
    assert (
        "Workload only_when_var_is_foo generated zero valid experiments because they were "
        "all filtered out by the workload's internal clauses." in out
    )
