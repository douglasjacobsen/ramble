# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
import ramble.config
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_variant_propagation_in_new_workspace(
    mutable_config, mutable_mock_workspace_path, request
):
    ws_name = request.node.name
    ramble.config.add("variants:package_manager:spack")
    ramble.config.add("variants:workflow_manager:slurm")
    with ramble.workspace.create(ws_name) as ws1:
        ws1.write()

        config_path = ws1.config_file_path

        with open(config_path) as f:
            data = f.read()
            assert "package_manager: spack" in data
            assert "workflow_manager: slurm" in data
