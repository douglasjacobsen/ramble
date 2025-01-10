# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import re

from ramble.modkit import *
from ramble.util.hashing import hash_string


class Docker(BasicModifier):
    """Docker is a set of platform as a service (PaaS) products that use
    OS-level virtualization to deliver software in packages called
    containers. The service has both free and premium tiers. The software
    that hosts the containers is called Docker Engine. It was first released
    in 2013 and is developed by Docker, Inc."""

    name = "docker"

    tags("container")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode for docker")
    default_mode("standard")

    required_variable(
        "container_uri",
        description="The variable controls the URI the container is pulled from. "
        "This should be of the format that would be input into `docker pull <uri>`.",
    )

    modifier_variable(
        "container_mounts",
        default="",
        description="Comma delimited list of mount points for the container. Filled in by modifier",
        modes=["standard"],
    )

    modifier_variable(
        "container_env_vars",
        default="",
        description="Comma delimited list of environments to import into container. Filled in by modifier",
        modes=["standard"],
    )

    modifier_variable(
        "container_extract_dir",
        default="{workload_input_dir}",
        description="Directory where the extracted paths will be stored",
        modes=["standard"],
    )

    modifier_variable(
        "container_extract_paths",
        default="[]",
        description="List of paths to extract from the sqsh file into the {workload_input_dir}. "
        + "Will have paths of {workload_input_dir}/enroot_extractions/{path_basename}",
        modes=["standard"],
        track_used=False,
    )

    modifier_variable(
        "docker_run_args",
        default="-v {container_mounts}",
        description="Arguments to pass into `docker run` while executing the experiments",
        modes=["standard"],
    )

    variable_modification(
        "mpi_command",
        "docker run {docker_run_args} {container_uri}",
        method="append",
        modes=["standard"],
    )

    def __init__(self, file_path):
        super().__init__(file_path)

        self.docker_runner = None

    def _build_commands(self, app_inst=None, dry_run=False):
        """Construct command runner for docker"""

        if self.docker_runner is None:
            self.docker_runner = CommandRunner(
                name="docker",
                command="docker",
                dry_run=dry_run,
            )

    register_phase(
        "define_container_variables",
        pipeline="setup",
        run_before=["get_inputs"],
    )

    def _define_container_variables(self, workspace, app_inst=None):
        """Define helper variables for working with enroot experiments

        To ensure it is defined properly, construct a comma delimited list of
        environment variable names that will be added into the
        container_env_vars variable.
        """

        def extract_names(itr, name_set=set()):
            """Extract names of environment variables from the environment variable action sets

            Given an iterator over environment variable action sets, extract
            the names of the environment variables.

            Modifies the name_set argument inplace.
            """
            for action, conf in itr:
                if action in ["set", "unset"]:
                    for name in conf:
                        name_set.add(name)
                elif action == "prepend":
                    for group in conf:
                        for name in group["paths"]:
                            name_set.add(name)
                elif action == "append":
                    for group in conf:
                        for name in group["vars"]:
                            name_set.add(name)

        # Only define variables if mode is standard
        if self._usage_mode == "standard":
            # Define container_env-vars
            set_names = set()

            for env_var_set in app_inst._env_variable_sets:
                extract_names(env_var_set.items(), set_names)

            for mod_inst in app_inst._modifier_instances:
                extract_names(mod_inst.all_env_var_modifications(), set_names)

            env_var_list = ",".join(set_names)
            app_inst.define_variable("container_env_vars", env_var_list)

            # Define container_mounts
            input_mounts = app_inst.expander.expand_var("{container_mounts}")

            exp_mount = "{experiment_run_dir}:{experiment_run_dir}"
            expanded_exp_mount = app_inst.expander.expand_var(exp_mount)

            if (
                exp_mount not in input_mounts
                and expanded_exp_mount not in input_mounts
            ):
                add_mod = self._usage_mode not in self.variable_modifications
                add_mod = add_mod or (
                    self._usage_mode in self.variable_modifications
                    and "container_mounts"
                    not in self.variable_modifications[self._usage_mode]
                )
                if add_mod:
                    self.variable_modification(
                        "container_mounts",
                        modification=exp_mount,
                        separator=",",
                        method="append",
                        mode=self._usage_mode,
                    )

    register_phase(
        "pull_container",
        pipeline="setup",
        run_after=["get_inputs"],
        run_before=["make_experiments"],
    )

    def _pull_container(self, workspace, app_inst=None):
        """Pull the container uri using docker"""

        self._build_commands(app_inst, workspace.dry_run)

        uri = self.expander.expand_var_name("container_uri")

        pull_args = ["pull", uri]

        self.docker_runner.execute(self.docker_runner.command, pull_args)

    def artifact_inventory(self, workspace, app_inst=None):
        """Return hash of container uri and sqsh file if they exist

        Args:
            workspace (Workspace): Reference to workspace
            app_inst (ApplicationBase): Reference to application instance

        Returns:
            (dict): Artifact inventory for container attributes
        """

        self._build_commands(app_inst, workspace.dry_run)

        id_regex = re.compile(r'Id.*sha256:(?P<id>\S+)"')
        container_uri = self.expander.expand_var_name("container_uri")

        inventory = []
        inspect_args = ["inspect", container_uri]

        info = self.docker_runner.execute(
            self.docker_runner.command, inspect_args, return_output=True
        )

        container_id = None
        search_match = None
        if info:
            search_match = id_regex.search(info)

        if search_match:
            container_id = search_match.group("id")
        else:
            container_id = hash_string(container_uri)

        inventory.append(
            {
                "container_uri": container_uri,
                "container_id": container_id,
            }
        )

        return inventory
