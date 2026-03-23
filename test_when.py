import re

with open('var/ramble/repos/builtin/base_classes/application-base/base_class.py', 'r') as f:
    content = f.read()

# Instead of checking string 'False', the original code used `if self.expander.satisfies(var_when_set, self.experiment_variants())`
# If `var_when_set == False` (boolean), `satisfies(False)` evaluates to `True` always!
# Wait! In Ramble, `when=False` means "always apply"! `when=True` means what?
# "when=False" is the default value for the `when` parameter in directives!
# Let's fix my multi-pass PASS 1 to correctly check if `var_when_set` is exactly `False` or `"False"`.

def replace_set_variables_and_variants(content):
    new_method = """    def set_variables_and_variants(self, variables, variants, experiment_set):
        \"\"\"Set internal reference to variables and variants

        Also, create an application specific expander class.

        Args:
            variables (dict): Dictionary of variable definitions for this
                             experiment.
            variants (dict): Dictionary of variant controls for this
                             experiment.
            experiment_set: Reference to experiment set, for expanding
                            referenced variables.
        \"\"\"

        self.variables = variables.copy()
        self.variants = variants.copy()
        self.experiment_set = experiment_set
        self.expander = ramble.expander.Expander(
            self.variables, self.experiment_set
        )

        # Set application version or use preferred version if none specified
        _, _, maybe_version = self.expander.application_spec.partition("@")

        if maybe_version:
            super().set_version(
                version_number=maybe_version,
                description=self.expander.application_spec,
            )
        elif hasattr(self, "preferred_version"):
            super().set_version(
                version=self.preferred_version,
                description=self.expander.application_spec,
            )

        # ---------------------------------------------------------
        # PASS 1: Aggregate Variables
        # ---------------------------------------------------------

        aggregated_variables = {}

        # 1. Base objects (without package/workflow managers since we haven't loaded them yet)
        for _, obj in self._objects():
            # Add variables defined on the object unconditionally
            for var_when_set, var_list in obj.object_variables.items():
                if str(var_when_set) == 'False':
                    for var in var_list:
                        if var.name not in aggregated_variables:
                            aggregated_variables[var.name] = var.default

        # 2. Add workload variables unconditionally for Pass 1
        workloads = self.get_workloads()
        for workload in workloads:
            for var_when_set, var_list in workload.variables.items():
                if str(var_when_set) == 'False':
                    for var in var_list:
                        if var.name not in aggregated_variables:
                            aggregated_variables[var.name] = var.default

        # 3. User Workspace (Highest Precedence)
        for var_name, var_value in self.variables.items():
            aggregated_variables[var_name] = var_value

        # Update expander with Pass 1 aggregated variables so we can resolve variants
        self.expander._variables = aggregated_variables

        # ---------------------------------------------------------
        # PASS 2: Setup Variants and Resolve Configuration Merging
        # ---------------------------------------------------------

        # Define experiment variants
        for name, value in variants.items():
            expanded_value = self.expander.expand_var(value, typed=True)
            self.object_variants.experiment_variant(name, expanded_value)

        # Revert expander to original variables for the rest of the flow
        self.expander._variables = self.variables

        # Set up remaining variants
        self._set_package_manager()
        self._set_workflow_manager()

        base_chain = self.__class__.__mro__
        for cls in base_chain:
            if hasattr(cls, "name") and cls.name is not None:
                self.object_variants.multi_value_variant(
                    "application_name",
                    value=self.expander.application_name,
                )

        # Define workload_name variant as early as possible
        self.object_variants.default_variant(
            "workload_name",
            default=self.expander.workload_name,
            description="Name of experiment workload",
        )

        self.no_expand_vars = set()
        workloads = self.get_workloads()

        for workload in workloads:
            for var_when_set, var_list in workload.variables.items():
                if self.expander.satisfies(
                    var_when_set, self.experiment_variants(allow_caching=False)
                ):
                    for var in var_list:
                        if not var.expandable:
                            self.no_expand_vars.add(var.name)

        self.define_missing_variables()

        self.expander.set_no_expand_vars(self.no_expand_vars)
        if experiment_set and experiment_set._workspace:
            self.expander.replacement_paths = (
                experiment_set._workspace.workspace_paths()
            )"""

    start_idx = content.find('    def set_variables_and_variants(self, variables, variants, experiment_set):')
    end_idx = content.find('    def non_reserved_variables(', start_idx)

    return content[:start_idx] + new_method + '\n\n' + content[end_idx:]

with open('var/ramble/repos/builtin/base_classes/application-base/base_class.py', 'w') as f:
    f.write(replace_set_variables_and_variants(content))
