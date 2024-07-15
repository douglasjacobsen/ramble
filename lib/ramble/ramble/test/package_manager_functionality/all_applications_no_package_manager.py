# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import deprecation

import pytest

from ramble.test.package_manager_functionality.app_helpers import dryrun_app_workloads


pytestmark = pytest.mark.usefixtures("mutable_mock_workspace_path")

# Generate tests for a single package manager, in order to parallelize across
# package managers for parallel tests. This is primarly because we use
# `--dist loadfile`


@pytest.mark.long
@deprecation.fail_if_not_removed
@pytest.mark.filterwarnings("ignore:invalid escape sequence:DeprecationWarning")
def test_all_applications_no_pkg_man(application):
    dryrun_app_workloads(application, "None")
