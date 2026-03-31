# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from unittest.mock import patch

import pytest

import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "mutable_mock_apps_repo",
    "mutable_mock_base_apps_repo",
    "mutable_mock_mods_repo",
    "workspace_deactivate",
)

workspace = RambleCommand("workspace")


def test_workspace_create_interactive_basic(mutable_mock_workspace_path):
    ws_name = "test_ws"

    inputs = [
        ws_name,  # Enter a name or directory path
        "basic",  # Enter the application name
        "test_wl",  # Enter the workload name
        "",  # Enter the package manager
        "",  # Enter the workflow manager
        "1",  # n_ranks
        "1",  # n_nodes
        "val1",  # foo.bar
        "val2",  # auto_env_var
    ]

    input_idx = 0

    def mock_input(*args, **kwargs):
        nonlocal input_idx
        if input_idx >= len(inputs):
            return ""
        val = inputs[input_idx]
        input_idx += 1
        return val

    yes_no_responses = [False, True, False]
    yes_no_idx = 0

    def mock_yes_no(*args, **kwargs):
        nonlocal yes_no_idx
        if yes_no_idx >= len(yes_no_responses):
            return False
        val = yes_no_responses[yes_no_idx]
        yes_no_idx += 1
        return val

    with patch("builtins.input", side_effect=mock_input):
        with patch("llnl.util.tty.get_yes_or_no", side_effect=mock_yes_no):
            workspace("create", "--interactive")

    assert ramble.workspace.exists(ws_name)
    ws = ramble.workspace.read(ws_name)

    found_basic = False
    found_test_wl = False
    with ws:
        for workloads, application_context in ws.all_applications():
            if application_context.context_name == "basic":
                found_basic = True
            for _, workload_context in ws.all_workloads(workloads):
                if workload_context.context_name == "test_wl":
                    found_test_wl = True

    assert found_basic
    assert found_test_wl


def test_workspace_create_interactive_vector_and_global_variants(mutable_mock_workspace_path):
    ws_name = "test_ws_vector"

    inputs = [
        ws_name,
        "basic",
        "test_wl",
        "spack-lightweight",
        "user-managed",
        "range(1, 5)",  # n_ranks as a vector string
        "[1, 2]",  # n_nodes as a vector list
        "val1",
        "val2",
    ]

    input_idx = 0

    def mock_input(*args, **kwargs):
        nonlocal input_idx
        if input_idx >= len(inputs):
            return ""
        val = inputs[input_idx]
        input_idx += 1
        return val

    # 1. Standalone? No
    # 2. Add app? Yes
    # 3. Global variants? Yes
    # 4. Add modifier? No
    yes_no_responses = [False, True, True, False]
    yes_no_idx = 0

    def mock_yes_no(*args, **kwargs):
        nonlocal yes_no_idx
        if yes_no_idx >= len(yes_no_responses):
            return False
        val = yes_no_responses[yes_no_idx]
        yes_no_idx += 1
        return val

    with patch("builtins.input", side_effect=mock_input):
        with patch("llnl.util.tty.get_yes_or_no", side_effect=mock_yes_no):
            workspace("create", "--interactive")

    assert ramble.workspace.exists(ws_name)
    ws = ramble.workspace.read(ws_name)

    with ws:
        workspace_dict = ws._get_workspace_dict()
        ramble_dict = workspace_dict["ramble"]

        # Verify global variants
        assert "variants" in ramble_dict
        assert ramble_dict["variants"]["package_manager"] == "spack-lightweight"
        assert ramble_dict["variants"]["workflow_manager"] == "user-managed"

        # Verify vector syntax
        exp_dict = ws._get_scope_section("basic:test_wl:generated")
        assert exp_dict["variables"]["n_ranks"] == "range(1, 5)"
        assert isinstance(exp_dict["variables"]["n_nodes"], list)
        assert exp_dict["variables"]["n_nodes"] == [1, 2]

        # Verify experiment does NOT have local variants
        assert "variants" not in exp_dict


def test_workspace_create_interactive_search_and_modifier(mutable_mock_workspace_path):
    ws_name = "test_ws_mod"

    # 1. ws_name
    # 2. search foo (fails to find basic)
    # 3. list (shows basic)
    # 4. basic
    # 5. list (shows test_wl)
    # 6. test_wl
    # 7. list (shows spack-lightweight)
    # 8. spack-lightweight
    # 9. list (shows user-managed)
    # 10. user-managed
    # 11. n_ranks
    # 12. n_nodes
    # 13. foo.bar
    # 14. auto_env_var
    # 15. list (modifiers)
    # 16. test-mod

    inputs = [
        ws_name,
        "search foo",
        "list",
        "basic",
        "list",
        "test_wl",
        "list",
        "spack-lightweight",
        "list",
        "user-managed",
        "1",
        "1",
        "v1",
        "v2",
        "list",
        "test-mod",
    ]

    input_idx = 0

    def mock_input(*args, **kwargs):
        nonlocal input_idx
        if input_idx >= len(inputs):
            return ""
        val = inputs[input_idx]
        input_idx += 1
        return val

    # 1. Standalone? No
    # 2. Add app? Yes
    # 3. Global variants? No
    # 4. Add modifier? Yes
    # 5. Global modifier? Yes
    # 6. Add another modifier? No
    yes_no_responses = [False, True, False, True, True, False]
    yes_no_idx = 0

    def mock_yes_no(*args, **kwargs):
        nonlocal yes_no_idx
        if yes_no_idx >= len(yes_no_responses):
            return False
        val = yes_no_responses[yes_no_idx]
        yes_no_idx += 1
        return val

    with patch("builtins.input", side_effect=mock_input):
        with patch("llnl.util.tty.get_yes_or_no", side_effect=mock_yes_no):
            workspace("create", "--interactive")

    assert ramble.workspace.exists(ws_name)
    ws = ramble.workspace.read(ws_name)

    with ws:
        found_mod = False
        workspace_dict = ws._get_workspace_dict()
        if "modifiers" in workspace_dict["ramble"]:
            for mod in workspace_dict["ramble"]["modifiers"]:
                if mod["name"] == "test-mod":
                    found_mod = True
        assert found_mod


def test_workspace_create_interactive_standalone(tmpdir):
    ws_path = str(tmpdir.join("standalone_ws"))

    inputs = [
        ws_path,  # Enter a name or directory path
        "basic",  # Enter the application name
        "test_wl",  # Enter the workload name
        "",  # Enter the package manager
        "",  # Enter the workflow manager
        "1",  # n_ranks
        "1",  # n_nodes
        "val1",  # foo.bar
        "val2",  # auto_env_var
    ]

    input_idx = 0

    def mock_input(*args, **kwargs):
        nonlocal input_idx
        if input_idx >= len(inputs):
            return ""
        val = inputs[input_idx]
        input_idx += 1
        return val

    # 1. Standalone directory? Yes
    # 2. Configure an application? Yes
    # 3. Add modifier? No
    yes_no_responses = [True, True, False]
    yes_no_idx = 0

    def mock_yes_no(*args, **kwargs):
        nonlocal yes_no_idx
        if yes_no_idx >= len(yes_no_responses):
            return False
        val = yes_no_responses[yes_no_idx]
        yes_no_idx += 1
        return val

    with patch("builtins.input", side_effect=mock_input):
        with patch("llnl.util.tty.get_yes_or_no", side_effect=mock_yes_no):
            workspace("create", "--interactive")

    assert os.path.isdir(ws_path)
    ws = ramble.workspace.Workspace(ws_path)

    found_basic = False
    with ws:
        for workloads, application_context in ws.all_applications():
            if application_context.context_name == "basic":
                found_basic = True

    assert found_basic
