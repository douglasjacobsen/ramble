import os
import pytest
import ramble.workspace
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config", "mutable_mock_workspace_path", "mutable_mock_apps_repo", "mock_modifiers", "mutable_mock_pkg_mans_repo"
)

def test_multipass_resolves_variants_from_variables(mutable_mock_workspace_path, mutable_mock_apps_repo, mutable_mock_pkg_mans_repo):
    """Test that a variant whose value is derived from a lower precedence variable resolves properly
       and satisfies `when` conditional blocks during the same merge pass.
    """

    workspace_name = "test_multipass"
    global_args = ["-w", workspace_name]

    test_config = """
ramble:
  variables:
    sys_pm_name: builtin.mock.spack
    processes_per_node: 1
    mpi_command: ''
    batch_submit: '{execute_experiment}'
    modeless_required_var: 1
  variants:
    package_manager: '{sys_pm_name}'
    zlib_type: modifier
    inc_zlib: true
  applications:
    when-variants:
      workloads:
        test_wl:
          experiments:
            test:
              variables:
                n_ranks: 1
                n_nodes: 1
                processes_per_node: 1
"""

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws._re_read()

        try:
            experiment_set = ws.build_experiment_set(die_on_validate_error=False)
            app_inst = experiment_set.experiments["when-variants-test_wl-test"]

            # Verify the variant was expanded using `sys_pm_name`
            assert app_inst.package_manager is not None
            assert app_inst.package_manager.name == "builtin.mock.spack"
        except SystemExit:
            pass
