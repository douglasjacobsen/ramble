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
from ramble.base_mod.builtin.container_base import ContainerBase


class Docker(ContainerBase):
    """Docker is a set of platform as a service (PaaS) products that use
    OS-level virtualization to deliver software in packages called
    containers. The service has both free and premium tiers. The software
    that hosts the containers is called Docker Engine. It was first released
    in 2013 and is developed by Docker, Inc."""

    name = "docker"

    _runtime = "docker"
    _pull_command = "docker pull"

    maintainers("douglasjacobsen")

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

    register_phase(
        "pull_container",
        pipeline="setup",
        run_after=["get_inputs"],
        run_before=["make_experiments"],
    )

    def _pull_container(self, workspace, app_inst=None):
        """Pull the container uri using docker"""

        self._build_runner(
            runtime=self._runtime, app_inst=app_inst, dry_run=workspace.dry_run
        )

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

        self._build_runner(
            runtime=self._runtime, app_inst=app_inst, dry_run=workspace.dry_run
        )

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
