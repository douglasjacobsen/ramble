# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for workflow manager definitions"""

from typing import List

from ramble.language.workflow_manager_language import (
    WorkflowManagerMeta,
    workflow_manager_variable,
)
from ramble.language.shared_language import SharedMeta
from ramble.util.naming import NS_SEPARATOR
import ramble.variants
import ramble.util.class_attributes
import ramble.util.directives
from ramble.expander import ExpanderError


class WorkflowManagerBase(metaclass=WorkflowManagerMeta):
    name = None
    object_variants = set()
    _builtin_name = NS_SEPARATOR.join(("workflow_manager_builtin", "{obj_name}", "{name}"))
    _language_classes = [WorkflowManagerMeta, SharedMeta]
    _pipelines = [
        "analyze",
        "setup",
        "execute",
    ]
    maintainers: List[str] = []
    tags: List[str] = []

    workflow_manager_variable(
        "workflow_banner",
        default="""# ****************************************************
# * No workflow is used with this experiment
# * Execution command: {batch_submit}
# * If this file is not the same as the above path, it is unlikely that this script
# * is used when `ramble on` executes experiments.
# ****************************************************
""",
        description="Banner to describe the workflow within execution templates",
    )

    workflow_manager_variable(
        "workflow_pragmas",
        default="",
        description="Pragmas to apply within execution templates for the workflow",
    )

    workflow_manager_variable(
        "workflow_hostfile_cmd",
        default="",
        description="Hostfile command to apply within execution templates for the workflow",
    )

    workflow_manager_variable(
        "hostfile", default="{experiment_run_dir}/hostfile", description="Default hostfile path"
    )

    def __init__(self, file_path):
        super().__init__()

        ramble.util.class_attributes.convert_class_attributes(self)

        self._file_path = file_path

        ramble.util.directives.define_directive_methods(self)

        ramble.variants.define_variant(self, "workflow_manager", default=self.name)

        self.app_inst = None
        self.runner = None

    def set_application(self, app_inst):
        """Set a reference to the associated app_inst"""
        self.app_inst = app_inst

    def get_status(self, workspace):
        """Return status of a given job"""
        return None

    def conditional_expand(self, templates):
        """Return a (potentially empty) list of expanded strings

        Args:
            templates: A list of templates to expand.
                If the template cannot be fully expanded, it's skipped.
        Returns:
            A list of expanded strings
        """
        expander = self.app_inst.expander
        expanded = []
        for tpl in templates:
            try:
                rendered = expander.expand_var(tpl, allow_passthrough=False)
                if rendered:
                    expanded.append(rendered)
            except ExpanderError:
                # Skip a particular entry if any of the vars are not defined
                continue
        return expanded

    def template_render_vars(self):
        """Define variables to be used in template rendering"""
        return {}

    def copy(self):
        """Deep copy a workflow manager instance"""
        new_copy = type(self)(self._file_path)

        return new_copy

    def __str__(self):
        return self.name
