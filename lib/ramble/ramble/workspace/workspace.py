# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import contextlib
import copy
import re
import shutil
import datetime
import fnmatch
from collections import defaultdict

import llnl.util.filesystem as fs
import llnl.util.tty as tty
import llnl.util.tty.log as log

import ramble.config
import ramble.paths
import ramble.util.path
import ramble.error
import ramble.repository
import ramble.experiment_set
import ramble.context
import ramble.util.web
import ramble.fetch_strategy
import ramble.util.install_cache
import ramble.success_criteria
import ramble.keywords
import ramble.software_environments
from ramble.mirror import MirrorStats

import spack.util.spack_yaml as syaml
import spack.util.spack_json as sjson
import spack.util.url as url_util
import spack.util.web as web_util

import ramble.schema.workspace
import ramble.schema.applications
import ramble.schema.merged

import ramble.util.lock as lk
from ramble.util.path import substitute_path_variables
from ramble.util.spec_utils import specs_equiv
import ramble.util.hashing
from ramble.namespace import namespace
import ramble.util.matrices
import ramble.util.env
from ramble.util.logger import logger
from ramble.util.conversions import list_str_to_list
import ramble.util.version

#: Environment variable used to indicate the active workspace
ramble_workspace_var = "RAMBLE_WORKSPACE"

#: Currently activated workspace
_active_workspace = None

#: Subdirectory where workspace configs are stored
workspace_config_path = "configs"

#: Name of subdirectory within workspaces where logs are stored
workspace_log_path = "logs"

#: Name of subdirectory within workspaces where experiments are stored
workspace_experiment_path = "experiments"

#: Name of subdirectory within workspaces where input files are stored
workspace_input_path = "inputs"

#: Name of subdirectory within workspaces where software environment
#: are stored
workspace_software_path = "software"

#: Name of the subdirectory where workspace archives are stored
workspace_archive_path = "archive"

#: Name of the subdirectory where shared/sourale files are stored
workspace_shared_path = "shared"

#: Name of the subdirectory where shared/sourale files are stored
workspace_shared_license_path = "licenses"

#: Name of the subdirectory where deployments are stored
workspace_deployments_path = "deployments"

#: regex for validating workspace names
valid_workspace_name_re = r"^\w[\w-]*$"

#: Config schema for application files
applications_schema = ramble.schema.applications.schema

#: Extension for template files
workspace_template_extension = ".tpl"

#: Directory name for auxiliary software files
auxiliary_software_dir_name = "auxiliary_software_files"

#: Config file information for workspaces.
#: Keys are filenames, values are dictionaries describing the config files.
config_schema = ramble.schema.workspace.schema
config_section = "workspace"
config_file_name = "ramble.yaml"
licenses_file_name = "licenses.yaml"

metadata_file_name = "workspace_metadata.yaml"

workspace_all_experiments_file = "all_experiments"

workspace_execution_template = "execute_experiment" + workspace_template_extension

#: Name of lockfile within a workspace
lockfile_name = "ramble.lock"


def valid_workspace_name(name):
    return re.match(valid_workspace_name_re, name)


def validate_workspace_name(name):
    if not valid_workspace_name(name):
        logger.debug(f"Validation failed for {name}")
        raise ValueError(
            (
                "'%s': names must start with a letter, and only contain "
                "letters, numbers, _, and -."
            )
            % name
        )
    return name


def activate(ws):
    """Activate a workspace.

    To activate a workspace, we add its configuration scope to the
    existing Ramble configuration, and we set active to the current
    workspace.

    Arguments:
        ws (Workspace): the workspace to activate
    """
    global _active_workspace

    # Fail early to avoid ending in an invalid state
    if not isinstance(ws, Workspace):
        raise TypeError(f"`ws` should be of type {Workspace.__name__}")

    # Check if we need to reinitialize the store due to pushing the configuration
    # below.
    prepare_config_scope(ws)

    logger.debug(f"Using workspace '{ws.root}'")

    # Do this last, because setting up the config must succeed first.
    _active_workspace = ws


def deactivate():
    """Undo any configuration settings modified by ``activate()``."""
    global _active_workspace

    if not _active_workspace:
        return

    logger.debug(f"Deactivated workspace '{_active_workspace.root}'")

    deactivate_config_scope(_active_workspace)

    _active_workspace = None


def prepare_config_scope(workspace):
    """Add workspace's scope to the global configuration search path."""
    for scope in workspace.config_scopes():
        ramble.config.config.push_scope(scope)


def deactivate_config_scope(workspace):
    """Remove any scopes from workspace from the global config path."""
    for scope in workspace.config_scopes():
        ramble.config.config.remove_scope(scope.name)


def all_workspace_names():
    """List the names of workspaces that currently exist."""
    # just return empty if the workspace path does not exist.  A read-only
    # operation like list should not try to create a directory.
    wspath = get_workspace_path()
    if not os.path.exists(wspath):
        return []

    candidates = sorted(os.listdir(wspath))
    names = []
    for candidate in candidates:
        configured = True
        yaml_path = os.path.join(_root(candidate), workspace_config_path, config_file_name)
        if not os.path.exists(yaml_path):
            configured = False
        if valid_workspace_name(candidate) and configured:
            names.append(candidate)
    return names


def all_workspaces():
    """Generator for all named workspaces."""
    for name in all_workspace_names():
        yield read(name)


def active_workspace():
    """Returns the active workspace when there is any"""
    return _active_workspace


def get_workspace_path():
    """Returns current directory of ramble-managed workspaces"""
    path_in_config = ramble.config.get("config:workspace_dirs")
    if not path_in_config:
        # command above should have worked, so if it doesn't, error out:
        logger.die("No config:workspace_dirs setting found in configuration!")

    wspath = ramble.util.path.canonicalize_path(str(path_in_config))
    return wspath


def _root(name):
    """Non-validating version of root(), to be used internally."""
    wspath = get_workspace_path()
    return os.path.join(wspath, name)


def root(name):
    """Get the root directory for a workspace by name."""
    validate_workspace_name(name)
    return _root(name)


def license_path(name):
    """Get the path to the shared license include for a workspace by name."""
    shared_license_path = os.path.join(workspace_shared_path, workspace_shared_license_path)
    os.path.join(root(name), shared_license_path)
    return _root(name)


def exists(name):
    """Whether a workspace with this name exists or not."""
    if not valid_workspace_name(name):
        return False
    return os.path.isdir(root(name))


def active(name):
    """True if the named workspace is active."""
    return _active_workspace and name == _active_workspace.name


def get_filepath(path, file_name):
    if is_workspace_dir(path):
        return os.path.join(path, workspace_config_path, file_name)
    return None


def config_file(path):
    """Returns the path to a workspace's ramble.yaml"""
    return get_filepath(path, config_file_name)


def licenses_file(path):
    """Returns the path to a workspace's licenses.yaml"""
    return get_filepath(path, licenses_file_name)


def all_config_files(path):
    """Returns path to all yaml files in workspace config directory"""
    config_files = []

    config_path = os.path.join(path, workspace_config_path)
    for f in os.listdir(config_path):
        if f.endswith(".yaml"):
            config_files.append(os.path.join(config_path, f))

    return config_files


def template_path(ws_path, requested_template_name):
    """Returns the path to a workspace's template file"""
    config_path = os.path.join(ws_path, workspace_config_path)
    template_file = requested_template_name + workspace_template_extension
    template_path = os.path.join(config_path, template_file)
    return template_path


def all_template_paths(path):
    """Returns (abs) path to available template files in the workspace"""
    templates = []

    config_path = os.path.join(path, workspace_config_path)
    for f in os.listdir(config_path):
        if f.endswith(workspace_template_extension):
            templates.append(os.path.join(config_path, f))

    return templates


def is_workspace_dir(path):
    """Whether a directory contains a ramble workspace."""
    ret_val = os.path.isdir(path)
    if ret_val:
        ret_val = ret_val and os.path.exists(
            os.path.join(path, workspace_config_path, config_file_name)
        )
    return ret_val


def create(name, read_default_template=True):
    """Create a named workspace in Ramble"""
    validate_workspace_name(name)
    if exists(name):
        raise RambleWorkspaceError("'%s': workspace already exists" % name)
    return Workspace(root(name), read_default_template=read_default_template)


def config_dict(yaml_data):
    """Get the configuration scope section out of a ramble.yaml"""
    key = ramble.config.first_existing(yaml_data, ramble.schema.workspace.keys)
    return yaml_data[key]


def get_workspace(args, cmd_name, required=False):
    """Used by commands to get the active workspace.

    This first checks for a ``workspace`` argument, then looks at the
    ``active`` workspace.  We check args first because Ramble's
    subcommand arguments are parsed *after* the ``-s`` and ``-D``
    arguments to ``ramble``.  So there may be a ``workspace``
    argument that is *not* the active workspace, and we give it
    precedence.

    This is used by a number of commands for determining whether there is
    an active workspace.

    If a workspace is not found *and* is required, print an error
    message that says the calling command *needs* an active
    workspace.

    Arguments:
        args (ramble.namespace): argparse namespace with command arguments
        cmd_name (str): name of calling command
        required (bool): if ``True``, raise an exception when no workspace
                         is found; if ``False``, just return ``None``

    Returns:
        (Workspace): if there is an arg or active workspace
    """

    logger.debug("In get_workspace()")

    workspace = getattr(args, "workspace", None)
    if workspace:
        if exists(workspace):
            return read(workspace)
        elif is_workspace_dir(workspace):
            return Workspace(workspace)
        else:
            raise RambleWorkspaceError("no workspace in %s" % workspace)

    # try the active workspace. This is set by find_workspace (above)
    if _active_workspace:
        return _active_workspace
    # elif not required:
    else:
        logger.die(
            f"`ramble {cmd_name}` requires a workspace",
            "activate a workspace first:",
            "    ramble workspace activate WRKSPC",
            "or use:",
            f"    ramble -w WRKSPC {cmd_name} ...",
        )


class Workspace:
    """Class representing a working directory for workload
    experiments

    Each workspace must have a config directory, that contains 2
    files by default.

    - ramble.yaml
    - execute_experiment.tpl

    The ramble.yaml file is the overall configuration file for
    this workspace. It defines all experiments, variables, and
    the entire software stack.

    The execute_experiment.tpl file is a template script that
    constants the blueprints for running each experiment.
    There are several ramble language features that can be used
    within the script, to help it render properly for all
    experiments.

    Each file with the suffix of .tpl will be expanded into the
    experiment directory, with the .tpl suffix removed.

    Directories will be created for each experiment, when the
    relevant phase of the application is executed. The workspace
    provides a self contained execution environment where experiments
    can be performed.
    """

    inventory_file_name = "ramble_inventory.json"
    hash_file_name = "workspace_hash.sha256"

    def __init__(self, root, dry_run=False, read_default_template=True):
        logger.debug(f"In workspace init. Root = {root}")
        self.root = ramble.util.path.canonicalize_path(root)
        self.txlock = lk.Lock(self._transaction_lock_path)
        self.dry_run = dry_run
        self.repeat_success_strict = True

        self.read_default_template = read_default_template
        self.configs = ramble.config.ConfigScope("workspace", self.config_dir)
        self._templates = {}
        self._auxiliary_software_files = {}
        self.software_mirror_path = None
        self.input_mirror_path = None
        self.mirror_existed = None
        self.software_mirror_stats = None
        self.input_mirror_stats = None
        self.input_mirror_cache = None
        self.software_mirror_cache = None
        self.software_environments = None
        self.metadata = syaml.syaml_dict()
        self.hash_inventory = {"experiments": [], "versions": []}
        version = ramble.util.version.get_version()
        self.hash_inventory["versions"].append(
            {
                "name": "ramble",
                "version": version,
                "digest": ramble.util.hashing.hash_string(version),
            }
        )

        self.workspace_hash = None

        self.specs = []

        self.config_sections = {}

        self.install_cache = ramble.util.install_cache.SetCache()

        # A per-package_manager dict mapping package spec to its install prefix.
        # This can be re-used by all experiments of the workspace.
        self.pkg_path_cache = defaultdict(dict)

        self.results = self.default_results()

        self.success_list = ramble.success_criteria.ScopedCriteriaList()

        # Key for each application config should be it's filepath
        # Format for an application config should be:
        #  {
        #     'filename': <filename>,
        #     'path': <filepath>,
        #     'raw_yaml': <raw_yaml>,
        #     'yaml': <yaml>
        #  }
        self.application_configs = {}

        self.experiments_script = None

        self._read()

        # Create a logger to redirect certain prints from screen to log file
        self.logger = log.log_output(echo=False, debug=tty.debug_level())

        self.deployment_name = self.name

    def _re_read(self):
        """Reinitialize the workspace object if it has been written (this
        may not be true if the workspace was just created in this running
        instance of ramble)."""
        for _, section in self.config_sections.items():
            if not os.path.exists(section["filename"]):
                return

        self.clear()
        self._read()

    def _read(self):
        # Create the workspace config section
        with lk.ReadTransaction(self.txlock):
            self.config_sections["workspace"] = {
                "filename": self.config_file_path,
                "path": self.config_file_path,
                "schema": config_schema,
                "section_filename": self.config_file_path,
                "raw_yaml": None,
                "yaml": None,
            }

            keywords = ramble.keywords.keywords

            read_default = not os.path.exists(self.config_file_path)
            if read_default:
                self._read_config(config_section, self._default_config_yaml())
            else:
                with open(self.config_file_path) as f:
                    self._read_config(config_section, f)

            read_default_script = self.read_default_template
            ext_len = len(workspace_template_extension)
            if os.path.exists(self.config_dir):
                for filename in os.listdir(self.config_dir):
                    if filename.endswith(workspace_template_extension):
                        read_default_script = False
                        template_name = filename[0:-ext_len]
                        template_path = os.path.join(self.config_dir, filename)
                        if keywords.is_reserved(template_name):
                            raise RambleInvalidTemplateNameError(
                                f"Template file {filename} results in a "
                                f"template name of {template_name}"
                                + " which is reserved by ramble."
                            )

                        with open(template_path) as f:
                            self._read_template(template_name, f.read())

                if os.path.exists(self.auxiliary_software_dir):
                    for filename in os.listdir(self.auxiliary_software_dir):
                        aux_file_path = os.path.join(self.auxiliary_software_dir, filename)
                        with open(aux_file_path) as f:
                            self._read_auxiliary_software_file(filename, f.read())

            if read_default_script:
                template_name = workspace_execution_template[0:-ext_len]
                self._read_template(template_name, self._template_execute_script())

            self._read_metadata()

    @classmethod
    def _template_execute_script(self):
        shell = ramble.config.get("config:shell")
        shell_path = os.path.join("/bin/", shell)
        script = (
            f"#!{shell_path}\n"
            + """\
# This is a template execution script for
# running the execute pipeline.
#
# Variables surrounded by curly braces will be expanded
# when generating a specific execution script.
# Some example variables are:
#   - experiment_run_dir (Will be replaced with the experiment directory)
#   - command (Will be replaced with the command to run the experiment)
#   - log_dir (Will be replaced with the logs directory)
#   - experiment_name (Will be replaced with the name of the experiment)
#   - workload_run_dir (Will be replaced with the directory of the workload
#   - application_name (Will be repalced with the name of the application)
#   - n_nodes (Will be replaced with the required number of nodes)
#   Any experiment parameters will be available as variables as well.

{workflow_banner}

cd "{experiment_run_dir}"

{command}
"""
        )

        return script

    @classmethod
    def _default_config_yaml(self):
        return """\
# This is a ramble workspace config file.
#
# It describes the experiments, the software stack
# and all variables required for ramble to configure
# experiments.
# As an example, experiments can be defined as follows.
# applications:
#   hostname: # Application name, as seen in `ramble list`
#     variables:
#       iterations: '5'
#     workloads:
#       serial: # Workload name, as seen in `ramble info <app>`
#         variables:
#           type: 'test'
#         experiments:
#           single_node: # Arbitrary experiment name
#             variables:
#               n_ranks: '{processes_per_node}'

ramble:
  env_vars:
    set:
      OMP_NUM_THREADS: '{n_threads}'
  variables:
    mpi_command: mpirun -n {n_ranks}
    batch_submit: '{execute_experiment}'
    processes_per_node: 1
  applications: {}
  software:
    packages: {}
    environments: {}
"""

    def _read_application_config(self, path, f, raw_yaml=None):
        """Read an application configuration file"""
        if path not in self.application_configs:
            self.application_configs[path] = {
                "filename": os.path.basename(path),
                "path": path,
                "schema": applications_schema,
                "raw_yaml": None,
                "yaml": None,
            }

        config = self.application_configs[path]
        self._read_yaml(config, f, raw_yaml)

    def _read_config(self, section, f, raw_yaml=None):
        """Read configuration file"""
        config = self.config_sections[section]
        self._read_yaml(config, f, raw_yaml)
        self._check_deprecated(config["yaml"])

    def _read_metadata(self):
        """Read workspace metadata file

        If a metadata file exists in the workspace root, read it in, and
        populate this workspace's metadata object with its contents.
        """
        metadata_file_path = os.path.join(self.root, metadata_file_name)

        if os.path.exists(metadata_file_path):
            with open(metadata_file_path) as f:
                self.metadata = syaml.load(f)
        else:
            self.metadata = syaml.syaml_dict()
            self.metadata[namespace.metadata] = syaml.syaml_dict()

    def _write_metadata(self):
        """Write out workspace metadata file

        Create, and populate the metadata file in the root of the workspace.
        This file can be used to house cross-pipeline information.
        """
        metadata_file_path = os.path.join(self.root, metadata_file_name)

        with open(metadata_file_path, "w+") as f:
            syaml.dump(self.metadata, stream=f)

    def _check_deprecated(self, config):
        """
        Trap and warn (or error) on deprecated configuration settings
        in the workspace config.
        """

        error_sections = []
        deprecated_sections = []

        if len(deprecated_sections) > 0:
            logger.warn("Your workspace configuration contains deprecated sections:")
            for section in deprecated_sections:
                logger.warn(f"     {section}")
            logger.warn("Please see the current workspace documentation and update")
            logger.warn("to ensure your workspace continues to function properly")

        if len(error_sections) > 0:
            logger.warn("Your workspace configuration contains invalid sections:")
            for section in deprecated_sections:
                logger.warn(f"     {section}")
            logger.die("Please update to the latest format.")

    def _read_yaml(self, config, f, raw_yaml=None):
        if raw_yaml:
            _, config["yaml"] = _read_yaml(f, config["schema"])
            config["raw_yaml"], _ = _read_yaml(raw_yaml, config["schema"])
        else:
            config["raw_yaml"], config["yaml"] = _read_yaml(f, config["schema"])

    def _read_template(self, name, f):
        """Read a template file"""
        self._templates[name] = {
            "contents": f,
            "digest": ramble.util.hashing.hash_string(f),
        }

    def _read_auxiliary_software_file(self, name, f):
        """Read an auxiliary software file for generated software directories"""
        self._auxiliary_software_files[name] = f

    def write(self, software_dir=None, inputs_dir=None):
        """Write an in-memory workspace to its location on disk."""

        with lk.WriteTransaction(self.txlock, acquire=self._re_read):
            # Ensure required directory structure exists
            fs.mkdirp(self.path)
            fs.mkdirp(self.config_dir)
            fs.mkdirp(self.auxiliary_software_dir)
            fs.mkdirp(self.log_dir)
            fs.mkdirp(self.experiment_dir)

            if inputs_dir:
                os.symlink(os.path.abspath(inputs_dir), self.input_dir, target_is_directory=True)
            elif not os.path.exists(self.input_dir):
                fs.mkdirp(self.input_dir)

            if software_dir:
                os.symlink(
                    os.path.abspath(software_dir), self.software_dir, target_is_directory=True
                )
            elif not os.path.exists(self.software_dir):
                fs.mkdirp(self.software_dir)

            fs.mkdirp(self.shared_dir)
            fs.mkdirp(self.shared_license_dir)

            self._write_config(config_section)

            self._write_templates()

            self._write_metadata()

    def _write_config(self, section, force=False):
        """Update YAML config file for this workspace, based on
        changes and write it"""
        config = self.config_sections[section]

        changed = not yaml_equivalent(config["raw_yaml"], config["yaml"])
        written = os.path.exists(config["path"])
        if changed or not written or force:
            config["raw_yaml"] = copy.deepcopy(config["yaml"])
            with fs.write_tmp_and_move(config["path"]) as f:
                _write_yaml(config["yaml"], f, config["schema"])

    def _write_templates(self):
        """Write all templates out to workspace"""

        for name, conf in self._templates.items():
            template_path = self.template_path(name)
            with open(template_path, "w+") as f:
                f.write(conf["contents"])

    def get_metadata(self, key):
        """Get the value of a metadata key

        Args:
            key (str): Name of metadata key to retrieve

        Returns:
            (any): Value associated with key in metadata
        """
        if key in self.metadata[namespace.metadata]:
            return self.metadata[namespace.metadata][key]
        else:
            return None

    def update_metadata(self, key, value):
        """Set the metadata key value

        Args:
            key (str): Key of metadata to set
            value (any): Value to set in the metadata object
        """
        self.metadata[namespace.metadata][key] = value

    def clear(self):
        self.config_sections = {}
        self.application_configs = []
        self._previous_active = None  # previously active environment
        self.specs = []

    def extract_success_criteria(self, scope, contents):
        """Extract success citeria, and inject it into the scoped list

        Extract success criteria from a contents dictionary, and inject it into
        the scoped success list within the right scope.
        """
        self.success_list.flush_scope(scope)

        if namespace.success in contents:
            logger.debug(" ---- Found success in %s" % scope)
            for conf in contents[namespace.success]:
                logger.debug(" ---- Adding criteria %s" % conf["name"])
                self.success_list.add_criteria(scope, **conf)

    def all_specs(self):
        import ramble.spec

        specs = []
        for app, workloads, *_ in self.all_applications():
            for workload, *_ in self.all_workloads(workloads):
                app_spec = ramble.spec.Spec(app)
                app_spec.workloads[workload] = True
                specs.append(app_spec)

        return specs

    @property
    def all_experiments_path(self):
        return os.path.join(self.root, workspace_all_experiments_file)

    def build_experiment_set(self):
        """Create an experiment set representing this workspace"""

        experiment_set = ramble.experiment_set.ExperimentSet(self)

        experiment_set.set_base_var("experiments_file", self.all_experiments_path)

        for workloads, application_context in self.all_applications():
            experiment_set.set_application_context(application_context)

            for experiments, workload_context in self.all_workloads(workloads):
                experiment_set.set_workload_context(workload_context)

                for _, experiment_context in self.all_experiments(experiments):
                    experiment_set.set_experiment_context(experiment_context)

        experiment_set.build_experiment_chains()

        return experiment_set

    def all_applications(self):
        """Iterator over applications

        Returns application, context
        where context contains the platform level variables that
        should be applied.
        """

        ws_dict = self._get_workspace_dict()
        logger.debug(f" With ws dict: {ws_dict}")

        # Iterate over applications in ramble.yaml first
        app_dict = ramble.config.config.get_config("applications")

        for application, contents in app_dict.items():
            application_context = ramble.context.create_context_from_dict(application, contents)

            self.extract_success_criteria("application", contents)

            yield contents, application_context

        logger.debug("  Iterating over configs in directories...")
        # Iterate over applications defined in application directories
        # files after the ramble.yaml file is complete
        for app_conf in self.application_configs:
            config = self._get_application_dict_config(app_conf)
            if namespace.application not in config:
                logger.msg(f"No applications in config file {app_conf}")
            app_dict = config[namespace.application]
            for application, contents in app_dict.items():
                application_context = ramble.context.create_context_from_dict(
                    application, contents
                )

                self.extract_success_criteria("application", contents)

                yield contents, application_context

    def all_workloads(self, application):
        """Iterator over workloads in an application dict

        Returns workload, context
        where context contains the application level variables that
        should be applied.
        """

        if namespace.workload not in application:
            logger.msg("No workloads in application")
            return

        workloads = application[namespace.workload]

        for workload, contents in workloads.items():
            workload_context = ramble.context.create_context_from_dict(workload, contents)

            self.extract_success_criteria("workload", contents)

            yield contents, workload_context

    def all_experiments(self, workload):
        """Iterator over experiments in a workload dict

        Returns experiment, context
        Where context contains the workload level variables that
        should be applied.
        """

        if namespace.experiment not in workload:
            logger.msg("No experiments in workload")
            return

        experiments = workload[namespace.experiment]
        for experiment, contents in experiments.items():
            experiment_context = ramble.context.create_context_from_dict(experiment, contents)

            self.extract_success_criteria("experiment", contents)

            yield contents, experiment_context

    def print_config(self):
        workspace_dict = self._get_workspace_dict()
        print(f"\n{syaml.dump(workspace_dict)}")

    def manage_environments(
        self,
        env_name,
        env_packages="",
        external_path=None,
        remove=False,
        overwrite=False,
    ):
        """Manipulate software environments

        Create, change, remove, and augment software environment definitions.

        Args:
            env_name (str): Name of environment to manipulate
            env_packages (str): (Optional) Comma delimited list of packages to add into
                                this environment
            external_path (str): (Optional) Path to external environment definition
            remove (bool): Whether the named environment should be removed from the workspace
            overwrite (bool): Whether new definition should overwrite existing definitions
        """

        package_list = []
        if env_packages:
            package_list = env_packages.split(",")

        if package_list and external_path is not None:
            logger.die("Can only manage environments with one of package_list or external_path")

        software_dict = self.get_software_dict().copy()

        if namespace.environments in software_dict:
            environments = software_dict[namespace.environments]
        else:
            environments = None

        # Ensure package dict is an syaml_dict, for formatting
        if not environments:
            software_dict[namespace.environments] = syaml.syaml_dict()
            environments = software_dict[namespace.environments]

        if remove:
            if env_name in environments:
                del environments[env_name]
        else:
            if env_name in environments:
                conflicting_type = (
                    namespace.external_env in environments[env_name]
                    and package_list
                    or namespace.packages in environments[env_name]
                    and external_path
                )

                if overwrite:
                    del environments[env_name]
                elif conflicting_type:
                    logger.die(
                        "Cannot convert between internal and "
                        "external environments without --overwrite"
                    )

            if env_name not in environments:
                environments[env_name] = syaml.syaml_dict()

            if package_list:
                environments[env_name][namespace.packages] = package_list.copy()

            elif external_path:
                environments[env_name][namespace.external_env] = external_path

        if not self.dry_run:
            ramble.config.config.update_config(
                namespace.software, software_dict, scope=self.ws_file_config_scope_name()
            )
        else:
            workspace_dict = self._get_workspace_dict()
            workspace_dict[namespace.software] = software_dict

    def manage_packages(
        self,
        pkg_name,
        pkg_spec="",
        compiler_pkg=None,
        compiler_spec=None,
        package_manager_prefix=None,
        remove=False,
        overwrite=False,
    ):
        """Manage workspace package definitions

        Create, remove, update, or augment package definitions.

        Args:
            pkg_name (str): Name of package to manipulate
            pkg_spec (str): Package spec for the package manager
            compiler_pkg (str): Name of the package to use as a compiler for this package
            compiler_spec (str): When this package is used as a compiler for
                                 another, the string to refer to this package.
            package_manager_prefix (str): A package manager specific prefix to
                                          apply to package attribute definitions
            remove (bool): Whether the named package should be removed from the workspace
            overwrite (bool): Whether colliding definitions should be overwritten
        """

        software_dict = self.get_software_dict().copy()

        if namespace.packages in software_dict:
            packages = software_dict[namespace.packages]
        else:
            packages = None

        # Ensure package dict is an syaml_dict, for formatting
        if not packages:
            software_dict[namespace.packages] = syaml.syaml_dict()
            packages = software_dict[namespace.packages]

        if remove:
            if pkg_name in packages:
                del packages[pkg_name]
        else:
            if not pkg_spec:
                logger.die("Cannot define a package without a --pkg-spec attribute")

            pkg_def = syaml.syaml_dict()
            prefix = ""
            if package_manager_prefix:
                prefix = f"{package_manager_prefix}_"

            pkg_def[f"{prefix}{namespace.pkg_spec}"] = pkg_spec
            if compiler_pkg:
                pkg_def[f"{prefix}{namespace.compiler}"] = compiler_pkg

            if compiler_spec:
                pkg_def[f"{prefix}{namespace.compiler_spec}"] = compiler_spec

            if pkg_name in packages:
                for attr, val in packages[pkg_name].items():
                    if attr in pkg_def and pkg_def[attr] != val and not overwrite:
                        logger.warn(
                            f"Cannot overwrite existing value of {attr} without --overwrite"
                        )
                        del pkg_def[attr]
            else:
                packages[pkg_name] = syaml.syaml_dict()

            for attr, val in pkg_def.items():
                packages[pkg_name][attr] = val

        if not self.dry_run:
            ramble.config.config.update_config(
                namespace.software, software_dict, scope=self.ws_file_config_scope_name()
            )
        else:
            workspace_dict = self._get_workspace_dict()
            workspace_dict[namespace.software] = software_dict

    def add_experiments(
        self,
        application,
        workload_name_variable,
        workload_filters,
        include_default_variables,
        variable_filters,
        variable_definitions,
        experiment_name,
        package_manager=None,
        zips=None,
        matrix=None,
        overwrite=False,
    ):
        """Add new experiments to this workspace

        Iterate over the workloads of the input application and define new
        experiments for each workload that matches any filter provided in
        workload_filters.

        Args:
            application (str): Name of application to define experiments for
            workload_name_variable (str): Name of variable to contain workload names,
                                          if the workload names should be collapsed
            workload_filters (list(str)): List of filters to downselect workloads with
            include_default_variables (bool): Whether to include default variables in the
                                              resulting config or not
            variable_filters (list(str)): List of filters to downselect variables with
            variable_definitions (list(str)): List of variable definitions to use
                                              within generated experiments
            experiment_name (str): The name of the experiments to add
            package_manager (str): Name of package manager to use for the generated experiments
            zips (list(str) | None): List of strings representing zips to define, in the
                              format zipname=[var1,var2,var3]
            matrix (str): String representing a matrix to define within the
                          experiment in the format of var1,var2,var3.
            overwrite (bool): Whether to overwrite existing definitions that
                              collide with new definitions or not.
        """

        if zips is None:
            zips = []

        def yaml_add_comment_before_key(
            base, key, comment, column=None, clear=False, start_char="#"
        ):
            """
            Insert a comment before the provided key within the base commented
            object.

            Args:
                base: Typically a CommentedMap, but the object comments should
                      be added to
                key: Key in base object to inject the comment before.
                column (int): Column to start the comment at. If not specified,
                              will use previously defined comments to determine
                              indentation.
                clear (bool): Whether to clear previous comments or not
                start_char (str): Character to begin the comment with
            """
            import ruamel.yaml as yaml

            key_comment = base.ca.items.setdefault(key, [None, [], None, None])

            if clear:
                key_comment[1] = []
            comment_list = key_comment[1]

            if comment:
                comment_start = f"{start_char} "
                if comment[-1] == "\n":
                    comment = comment[:-1]  # strip final newline if there
            else:
                comment_start = f"{start_char}"

            if column is None:
                if comment_list:
                    # if there already are other comments get the column from them
                    column = comment_list[-1].start_mark.column
                else:
                    column = 0

            start_mark = yaml.error.Mark(None, None, None, column, None, None)

            comment_list.append(
                yaml.tokens.CommentToken(comment_start + comment + "\n", start_mark, None)
            )

            return base

        import ruamel.yaml as yaml

        edited = False

        workspace_vars = self.get_workspace_vars()
        apps_dict = self.get_applications().copy()

        app_inst = ramble.repository.get(application)

        var_def_dict = {}
        def_regex = re.compile(r"(?P<key>.*)=(?P<value>.*)")
        for definition in variable_definitions:
            m = def_regex.match(definition)
            if m:
                key = m.group("key")
                value = list_str_to_list(m.group("value"))
                var_def_dict[key] = value
            else:
                logger.die(
                    f"Invalid variable definition provided: {definition}. "
                    + "Accepted form is 'key=value'"
                )

        if application not in apps_dict:
            apps_dict[application] = syaml.syaml_dict()
            apps_dict[application][namespace.workload] = syaml.syaml_dict()

        workloads_dict = apps_dict[application][namespace.workload]

        exp_zips = {}
        for zip_def in zips:
            m = def_regex.match(zip_def)
            if m:
                key = m.group("key")
                value = list_str_to_list(m.group("value"))
                exp_zips[key] = value
            else:
                logger.die(
                    f"Invalid zip definition provided: {zip_def}. "
                    + "Accepted form is 'zipname=[var1,var2,var3]'"
                )

        exp_matrix = []
        if matrix:
            for part in matrix.split(","):
                exp_matrix.append(part)

        workload_names = []
        for workload in app_inst.workloads.values():
            add_workload = False
            for wl_filter in workload_filters:
                if fnmatch.fnmatch(workload.name, wl_filter):
                    add_workload = True
                    break

            # Don't add this experiment if it already exists in the workspace
            if add_workload:
                if application in apps_dict:
                    subdict = apps_dict[application]
                    if namespace.workload in subdict:
                        subdict = subdict[namespace.workload]
                        if workload.name in subdict:
                            subdict = subdict[workload.name]
                            if namespace.experiment in subdict:
                                subdict = subdict[namespace.experiment]
                                if experiment_name in subdict:
                                    exp_name = f"{application}.{workload.name}.{experiment_name}"
                                    if not overwrite:
                                        logger.warn(
                                            f"Experiment {exp_name} is defined already. "
                                            + "To overwrite, use '--overwrite'"
                                        )
                                    add_workload = overwrite

            if add_workload:
                workload_names.append(workload.name)

        if workload_name_variable:
            var_def_dict[workload_name_variable] = workload_names.copy()
            workload_names = [ramble.expander.Expander.expansion_str(workload_name_variable)]

        for workload_name in workload_names:
            edited = True
            if workload_name not in workloads_dict:
                workloads_dict[workload_name] = syaml.syaml_dict()
                workloads_dict[workload_name][namespace.experiment] = syaml.syaml_dict()

            exps_dict = workloads_dict[workload_name][namespace.experiment]
            exps_dict[experiment_name] = syaml.syaml_dict()
            exp_dict = exps_dict[experiment_name]

            if package_manager is not None:
                exp_dict[namespace.variants] = syaml.syaml_dict()
                variants_dict = exp_dict[namespace.variants]
                variants_dict[namespace.package_manager] = package_manager

            if namespace.variables not in exp_dict:
                exp_dict[namespace.variables] = yaml.comments.CommentedMap()

            vars_dict = exp_dict[namespace.variables]

            # Ensure required variables are defined
            for key in app_inst.keywords.all_required_keys():
                if key not in workspace_vars:
                    vars_dict[key] = ""

            # Only extract variable defaults if requested.
            # This is mutually exclusive with workload_name_variable
            if include_default_variables:
                # At this point we should only have a valid workload name
                workload = app_inst.workloads[workload_name]
                if workload.variables:
                    first_var = True
                    for var in workload.variables.values():
                        keep_var = False
                        for var_filter in variable_filters:
                            if fnmatch.fnmatch(var.name, var_filter):
                                keep_var = True
                                break

                        if keep_var:
                            vars_dict[var.name] = var.default

                            # Add blank line before all variables except
                            # the first
                            if first_var:
                                first_var = False
                            else:
                                yaml_add_comment_before_key(
                                    vars_dict, var.name, "", column=17, start_char=""
                                )
                            if var.description:
                                yaml_add_comment_before_key(
                                    vars_dict, var.name, var.description, column=17
                                )
                            if len(var.values) > 1 or var.values[0] is not None:
                                yaml_add_comment_before_key(
                                    vars_dict,
                                    var.name,
                                    f"Suggested values: {var.values}",
                                    column=17,
                                )

                if workload.environment_variables:
                    if namespace.env_var not in exps_dict[experiment_name]:
                        exp_dict[namespace.env_var] = syaml.syaml_dict()
                        exp_dict[namespace.env_var]["set"] = syaml.syaml_dict()

                    env_vars_dict = exp_dict[namespace.env_var]["set"]

                    for env_var in workload.environment_variables.values():
                        env_vars_dict[env_var.name] = env_var.value

            # Add any variables that are defined to the variables dict
            if var_def_dict:
                vars_dict.update(var_def_dict)

            if exp_zips:
                if namespace.zips not in exp_dict:
                    exp_dict[namespace.zips] = exp_zips.copy()

            if exp_matrix:
                if namespace.matrix not in exp_dict:
                    exp_dict[namespace.matrix] = exp_matrix.copy()

        if edited and not self.dry_run:
            ramble.config.config.update_config(
                namespace.application, apps_dict, scope=self.ws_file_config_scope_name()
            )
        elif edited:
            workspace_dict = self._get_workspace_dict()
            workspace_dict[namespace.ramble][namespace.application] = apps_dict

    def concretize(self, force=False, quiet=False):
        """Concretize software definitions for defined experiments

        Extract suggested software for experiments defined in a workspace, and
        ensure the software environments are defined properly.

        Args:
            force (bool): Whether to overwrite conflicting definitions of named packages or not
            quiet (bool): Whether to silently ignore conflicts or not


        """
        full_software_dict = self.get_software_dict()

        if (
            namespace.packages not in full_software_dict
            or not full_software_dict[namespace.packages]
        ):
            full_software_dict[namespace.packages] = syaml.syaml_dict()
        if (
            namespace.environments not in full_software_dict
            or not full_software_dict[namespace.environments]
        ):
            full_software_dict[namespace.environments] = syaml.syaml_dict()

        packages_dict = full_software_dict[namespace.packages]
        environments_dict = full_software_dict[namespace.environments]

        self.software_environments = ramble.software_environments.SoftwareEnvironments(self)

        experiment_set = self.build_experiment_set()

        for _, app_inst, _ in experiment_set.all_experiments():
            app_inst.build_modifier_instances()
            env_name_str = app_inst.expander.expansion_str(ramble.keywords.keywords.env_name)
            env_name = app_inst.expander.expand_var(env_name_str)

            if app_inst.package_manager is None:
                continue

            compiler_dicts = [app_inst.compilers]
            for mod_inst in app_inst._modifier_instances:
                compiler_dicts.append(mod_inst.compilers)

            for compiler_dict in compiler_dicts:
                for comp, info in compiler_dict.items():
                    if fnmatch.fnmatch(app_inst.package_manager.name, info["package_manager"]):
                        if comp not in packages_dict or force:
                            packages_dict[comp] = syaml.syaml_dict()
                            packages_dict[comp]["pkg_spec"] = info["pkg_spec"]
                            ramble.config.add(
                                f'software:packages:{comp}:pkg_spec:{info["pkg_spec"]}',
                                scope=self.ws_file_config_scope_name(),
                            )
                            if "compiler_spec" in info and info["compiler_spec"]:
                                packages_dict[comp]["compiler_spec"] = info["compiler_spec"]
                                config_path = (
                                    f"software:packages:{comp}:"
                                    + f'compiler_spec:{info["compiler_spec"]}'
                                )
                                ramble.config.add(
                                    config_path, scope=self.ws_file_config_scope_name()
                                )
                            if "compiler" in info and info["compiler"]:
                                packages_dict[comp]["compiler"] = info["compiler"]
                                config_path = (
                                    f"software:packages:{comp}:" + f'compiler:{info["compiler"]}'
                                )
                                ramble.config.add(
                                    config_path, scope=self.ws_file_config_scope_name()
                                )
                        elif not quiet and not specs_equiv(info, packages_dict[comp]):
                            logger.debug(f"  Spec 1: {str(info)}")
                            logger.debug(f"  Spec 2: {str(packages_dict[comp])}")
                            raise RambleConflictingDefinitionError(
                                f"Compiler {comp} would be defined " "in multiple conflicting ways"
                            )

            logger.debug(f"Trying to define packages for {env_name}")
            app_packages = []
            if env_name in environments_dict:
                if namespace.packages in environments_dict[env_name]:
                    app_packages = environments_dict[env_name][namespace.packages].copy()

            software_dicts = [app_inst.software_specs]
            for mod_inst in app_inst._modifier_instances:
                software_dicts.append(mod_inst.software_specs)

            for software_dict in software_dicts:
                for spec_name, info in software_dict.items():
                    if fnmatch.fnmatch(app_inst.package_manager.name, info["package_manager"]):
                        logger.debug(f"    Found spec: {spec_name}")
                        if spec_name not in packages_dict or force:
                            packages_dict[spec_name] = syaml.syaml_dict()
                            packages_dict[spec_name]["pkg_spec"] = info["pkg_spec"]
                            if "compiler_spec" in info and info["compiler_spec"]:
                                packages_dict[spec_name]["compiler_spec"] = info["compiler_spec"]
                            if "compiler" in info and info["compiler"]:
                                packages_dict[spec_name]["compiler"] = info["compiler"]

                        elif not quiet and not specs_equiv(info, packages_dict[spec_name]):
                            logger.debug(f"  Spec 1: {str(info)}")
                            logger.debug(f"  Spec 2: {str(packages_dict[spec_name])}")
                            raise RambleConflictingDefinitionError(
                                f"Package {spec_name} would be defined in multiple "
                                "conflicting ways"
                            )

                        if spec_name not in app_packages:
                            app_packages.append(spec_name)

            if app_packages:
                if env_name not in environments_dict:
                    environments_dict[env_name] = syaml.syaml_dict()

                environments_dict[env_name][namespace.packages] = app_packages.copy()

        ramble.config.config.update_config(
            "software", full_software_dict, scope=self.ws_file_config_scope_name()
        )

        return

    def write_json_results(self):
        out_file = os.path.join(self.root, "results.json")
        with open(out_file, "w+") as f:
            sjson.dump(self.results, f)
        return out_file

    def default_results(self):
        res = {}

        if self.workspace_hash:
            res["workspace_hash"] = self.workspace_hash
        else:
            try:
                with open(os.path.join(self.root, self.hash_file_name)) as f:
                    res["workspace_hash"] = f.readline().rstrip()
            except OSError:
                res["workspace_hash"] = "Unknown.."

        res["workspace_name"] = self.name
        res["experiments"] = []

        return res

    def append_result(self, result):
        if not self.results:
            self.results = self.default_results()

        self.results["experiments"].append(result)

    def insert_result(self, result, insert_before_exp):
        """Insert a result before a specified experiment"""

        def search_exp_index(results_list, exp_to_search):
            for i, exp in enumerate(results_list):
                if exp["name"] == exp_to_search:
                    return i
            return None

        if not self.results:
            self.results = self.default_results()

        insert_index = search_exp_index(self.results["experiments"], insert_before_exp)

        tty.debug(f"Attempting to insert result before experiment {insert_before_exp}")
        if insert_index is not None:
            self.results["experiments"].insert(insert_index, result)
        else:
            tty.debug(f"Could not find {insert_before_exp}, appending result to end instead.")
            self.results["experiments"].append(result)

    def symlink_result(self, out_file, latest_file):
        """
        Create symlink of result file so that results.latest.txt always points
        to the most recent analysis. This clobbers the existing link
        """

        from ramble.util.file_util import create_symlink

        create_symlink(out_file, latest_file)

    def dump_results(self, output_formats=None, print_results=False, summary_only=False):
        """
        Write out result file in desired format

        This attempts to avoid the loss of previous results data by appending
        the datetime to the filename, but is willing to clobber the file
        results.latest.<extension>

        """

        if output_formats is None:
            output_formats = ["text"]

        if not self.results:
            self.results = {}

        results = _filter_results(self.results, summary_only=summary_only)

        results_written = []
        symlinks_updated = []

        dt = self.date_string()
        inner_delim = "."
        filename_base = "results" + inner_delim + dt
        latest_base = "results" + inner_delim + "latest"

        if "text" in output_formats:

            file_extension = ".txt"
            out_file = os.path.join(self.root, filename_base + file_extension)
            latest_file = os.path.join(self.root, latest_base + file_extension)

            results_written.append(out_file)

            with open(out_file, "w+") as f:
                f.write(f"From Workspace: {self.name} (hash: {results['workspace_hash']})\n")
                if "experiments" in results:
                    for exp in results["experiments"]:
                        f.write("Experiment %s figures of merit:\n" % exp["name"])
                        f.write("  Status = %s\n" % exp["RAMBLE_STATUS"])
                        if "TAGS" in exp:
                            f.write(f'  Tags = {exp["TAGS"]}\n')

                        if exp["N_REPEATS"] > 0:  # this is a base exp with summary of repeats
                            for context in exp["CONTEXTS"]:
                                f.write(f'  {context["display_name"]} figures of merit:\n')

                                fom_summary = {}
                                for fom in context["foms"]:
                                    name = fom["name"]
                                    if name not in fom_summary.keys():
                                        fom_summary[name] = []
                                    stat_name = fom["origin_type"]
                                    value = fom["value"]
                                    units = fom["units"]

                                    output = f"{stat_name} = {value} {units}\n"
                                    fom_summary[name].append(output)

                                for fom_name, fom_val_list in fom_summary.items():
                                    f.write(f"    {fom_name}:\n")
                                    for fom_val in fom_val_list:
                                        f.write(f"      {fom_val.strip()}\n")

                            # Print software section if it contains info
                            if "SOFTWARE" in exp and exp["SOFTWARE"]:
                                f.write("  Software definitions:\n")
                                for package_manager, packages in exp["SOFTWARE"].items():
                                    f.write(f"    {package_manager} packages:\n")
                                    for pkg in packages:
                                        f.write(f"      {pkg['name']} @{pkg['version']}\n")

                        else:
                            for context in exp["CONTEXTS"]:
                                f.write(f'  {context["display_name"]} figures of merit:\n')
                                for fom in context["foms"]:
                                    name = fom["name"]
                                    if fom["origin_type"] == "modifier":
                                        delim = "::"
                                        mod = fom["origin"]
                                        name = f"{fom['origin_type']}{delim}{mod}{delim}{name}"

                                    output = "{} = {} {}".format(name, fom["value"], fom["units"])
                                    f.write("    %s\n" % (output.strip()))

                            # Print software section if it contains info
                            if "SOFTWARE" in exp and exp["SOFTWARE"]:
                                f.write("  Software definitions:\n")
                                for package_manager, packages in exp["SOFTWARE"].items():
                                    f.write(f"    {package_manager} packages:\n")
                                    for pkg in packages:
                                        f.write(f"      {pkg['name']} @{pkg['version']}\n")

                else:
                    logger.msg("No results to write")

            symlinks_updated.append(latest_file)
            self.symlink_result(out_file, latest_file)

        if "json" in output_formats:
            file_extension = ".json"
            out_file = os.path.join(self.root, filename_base + file_extension)
            latest_file = os.path.join(self.root, latest_base + file_extension)
            results_written.append(out_file)
            with open(out_file, "w+") as f:
                sjson.dump(results, f)
            symlinks_updated.append(latest_file)
            self.symlink_result(out_file, latest_file)

        if "yaml" in output_formats:
            file_extension = ".yaml"
            out_file = os.path.join(self.root, filename_base + file_extension)
            latest_file = os.path.join(self.root, latest_base + file_extension)
            results_written.append(out_file)
            with open(out_file, "w+") as f:
                syaml.dump(results, stream=f)

            symlinks_updated.append(latest_file)
            self.symlink_result(out_file, latest_file)

        if not results_written:
            logger.die("Results were not written.")

        logger.all_msg("Results are written to:")
        for out_file in results_written:
            logger.all_msg(f"  {out_file}")
        logger.all_msg("Symlinks updated:")
        for symlink_path in symlinks_updated:
            logger.all_msg(f"  {symlink_path}")

        if print_results:
            with open(results_written[0]) as f:
                # Use tty directly to avoid cluttering the analyze log
                tty.msg(f"Results from the analysis pipeline:\n{f.read()}")

        return filename_base

    def create_mirror(self, mirror_root):
        parsed_url = url_util.parse(mirror_root)
        self.mirror_path = url_util.local_file_path(parsed_url)
        self.mirror_existed = web_util.url_exists(self.mirror_path)
        self.input_mirror_path = os.path.join(self.mirror_path, "inputs")
        self.software_mirror_path = os.path.join(self.mirror_path, "software")
        mirror_dirs = [self.mirror_path, self.input_mirror_path, self.software_mirror_path]
        for subdir in mirror_dirs:
            if not os.path.isdir(subdir):
                try:
                    fs.mkdirp(subdir)
                except OSError as e:
                    raise ramble.mirror.MirrorError(
                        "Cannot create directory '%s':" % subdir, str(e)
                    )

        self.software_mirror_stats = MirrorStats()
        self.input_mirror_stats = MirrorStats()
        self.input_mirror_cache = ramble.caches.MirrorCache(self.input_mirror_path)
        self.software_mirror_cache = ramble.caches.MirrorCache(self.software_mirror_path)

    def simplify(self):
        # First drop unused experiment templates from app dict so environments aren't rendered
        app_dict = ramble.config.config.get_config(
            namespace.application, scope=self.ws_file_config_scope_name()
        )

        # Build experiment sets to determine which templates never get used
        self.software_environments = ramble.software_environments.SoftwareEnvironments(self)
        experiment_set = self.build_experiment_set()
        logger.debug("Software environments:")
        logger.debug(str(self.software_environments))

        for _, app_inst in experiment_set.template_experiments():
            if app_inst.is_template and not app_inst.generated_experiments:
                app = app_inst.expander.application_name
                wl = app_inst.expander.workload_name
                exp = app_inst.expander.experiment_name

                try:
                    app_dict[app][namespace.workload][wl][namespace.experiment].pop(exp)
                    if not app_dict[app][namespace.workload][wl][namespace.experiment]:
                        app_dict[app][namespace.workload][wl].pop(namespace.experiment)
                    if not app_dict[app][namespace.workload][wl]:
                        app_dict[app][namespace.workload].pop(wl)
                    if not app_dict[app][namespace.workload]:
                        app_dict[app].pop(namespace.workload)
                    if not app_dict[app]:
                        app_dict.pop(app)
                except KeyError:
                    continue

        ramble.config.config.update_config(
            namespace.application, app_dict, scope=self.ws_file_config_scope_name()
        )

        # Regenerate environments without the unused templates to see which env never get rendered
        self.software_environments = ramble.software_environments.SoftwareEnvironments(self)
        software_environments = self.software_environments
        experiment_set = self.build_experiment_set()

        software_dict = ramble.config.config.get_config(
            namespace.software, scope=self.ws_file_config_scope_name()
        )
        package_dict = software_dict[namespace.packages]
        environments_dict = software_dict[namespace.environments]

        tty.debug("Removing configurations that do not spark joy.")
        for pkg in software_environments.unused_packages():
            if pkg.name in package_dict:
                tty.debug(f"Removing {pkg.name} from software packages")
                package_dict.pop(pkg.name)
        for env in software_environments.unused_environments():
            if env.name in environments_dict:
                tty.debug(f"Removing {env.name} from software environments")
                environments_dict.pop(env.name)

        ramble.config.config.update_config(
            namespace.software, software_dict, scope=self.ws_file_config_scope_name()
        )

    @property
    def latest_archive_path(self):
        return os.path.join(self.archive_dir, self.latest_archive)

    @property
    def latest_archive(self):
        if hasattr(self, "_latest_archive") and self._latest_archive:
            return self._latest_archive

        if os.path.exists(self.archive_dir):
            archive_dirs = []

            for subdir in os.listdir(self.archive_dir):
                archive_path = os.path.join(self.archive_dir, subdir)
                if os.path.isdir(archive_path) and not os.path.islink(archive_path):
                    archive_dirs.append(archive_path)

            if archive_dirs:
                latest_path = max(archive_dirs, key=os.path.getmtime)
                self._latest_archive = os.path.basename(latest_path)
                return self._latest_archive

        return None

    def date_string(self):
        now = datetime.datetime.now()
        return now.strftime("%Y-%m-%d_%H.%M.%S")

    @property
    def internal(self):
        """Whether this workspace is managed by Ramble."""
        wspath = get_workspace_path()
        return self.path.startswith(wspath)

    @property
    def name(self):
        """Human-readable representation of the workspace.

        The name of the workspace is the basename of its path
        """
        return os.path.basename(self.path)

    @property
    def path(self):
        """Location of the workspace"""
        return self.root

    @property
    def active(self):
        """True if this workspace is currently active."""
        return _active_workspace and self.path == _active_workspace.path

    @property
    def internal_subdir(self):
        """Subdirectory for housing ramble internals"""
        return os.path.join(self.root, ".ramble-workspace")

    @property
    def _transaction_lock_path(self):
        """The location of the lock file used to synchronize multiple
        processes updating the same workspace.
        """
        return os.path.join(self.internal_subdir, "transaction_lock")

    @property
    def experiment_dir(self):
        """Path to the experiment directory"""
        return os.path.join(self.root, workspace_experiment_path)

    @property
    def input_dir(self):
        """Path to the input directory"""
        return os.path.join(self.root, workspace_input_path)

    @property
    def software_dir(self):
        """Path to the software directory"""
        return os.path.join(self.root, workspace_software_path)

    @property
    def log_dir(self):
        """Path to the logs directory"""
        return os.path.join(self.root, workspace_log_path)

    @property
    def config_dir(self):
        """Path to the configuration file directory"""
        return os.path.join(self.root, workspace_config_path)

    @property
    def auxiliary_software_dir(self):
        """Path to the auxiliary software files directory"""
        return os.path.join(self.config_dir, auxiliary_software_dir_name)

    @property
    def config_file_path(self):
        """Path to the configuration file directory"""
        return os.path.join(self.config_dir, config_file_name)

    @property
    def archive_dir(self):
        """Path to the archive directory"""
        return os.path.join(self.root, workspace_archive_path)

    @property
    def shared_dir(self):
        """Path to the shared directory"""
        return os.path.join(self.root, workspace_shared_path)

    @property
    def deployments_dir(self):
        """Path to the deployments directory"""
        return os.path.join(self.root, workspace_deployments_path)

    @property
    def named_deployment(self):
        """Path to the specific deployment directory"""
        return os.path.join(self.deployments_dir, self.deployment_name)

    @property
    def shared_license_dir(self):
        """Path to the shared license directory"""
        return os.path.join(self.shared_dir, workspace_shared_license_path)

    def template_path(self, name):
        if name in self._templates.keys():
            return os.path.join(self.config_dir, name + workspace_template_extension)
        return None

    def all_templates(self):
        """Iterator over each template in the workspace"""
        yield from self._templates.items()

    def all_auxiliary_software_files(self):
        """Iterator over each file in $workspace/configs/auxiliary_software_files"""
        yield from self._auxiliary_software_files.items()

    @classmethod
    def get_workspace_paths(cls, root):
        """Construct dictionary of path replacements for workspace"""
        workspace_path_replacements = {
            "workspace_root": root,
            "workspace": root,
            "workspace_configs": os.path.join(root, workspace_config_path),
            "workspace_software": os.path.join(root, workspace_software_path),
            "workspace_logs": os.path.join(root, workspace_log_path),
            "workspace_inputs": os.path.join(root, workspace_input_path),
            "workspace_experiments": os.path.join(root, workspace_experiment_path),
            "workspace_shared": os.path.join(root, workspace_shared_path),
            "workspace_archives": os.path.join(root, workspace_archive_path),
            "workspace_deployments": os.path.join(root, workspace_deployments_path),
        }

        return workspace_path_replacements

    def workspace_paths(self):
        """Dictionary of path replacements for workspace"""
        if not hasattr(self, "_workspace_path_replacements"):
            self._workspace_path_replacements = self.get_workspace_paths(self.root)

        return self._workspace_path_replacements

    def add_include(self, new_include):
        """Add a new include to this workspace"""

        if namespace.include not in self.config_sections["workspace"]["yaml"][namespace.ramble]:
            self.config_sections["workspace"]["yaml"][namespace.ramble][namespace.include] = []
        includes = self.config_sections["workspace"]["yaml"][namespace.ramble][namespace.include]
        includes.append(new_include)
        self._write_config(config_section)

    def remove_include(self, index=None, pattern=None):
        """Remove one or more includes from this workspace.

        Args:
            index (optional): Numerical position of include to remove
            pattern (optional): String or pattern of include to remove.
                                Removes all matching includes.
        """

        if namespace.include not in self.config_sections["workspace"]["yaml"][namespace.ramble]:
            return

        includes = self.config_sections["workspace"]["yaml"][namespace.ramble][namespace.include]
        changed = False

        if index is not None:
            if index < 0 or index >= len(includes):
                logger.die(
                    f"Requested index {index} " "is outside of the range of existing includes."
                )
            includes.pop(index)
            changed = True

        if pattern is not None:
            remove_indices = []
            for idx, include in enumerate(includes):
                if fnmatch.fnmatch(include, pattern):
                    remove_indices.append(idx)

            for remove_idx in reversed(remove_indices):
                if remove_idx >= 0 and remove_idx < len(includes):
                    includes.pop(remove_idx)
                    changed = True

        if changed:
            self._write_config(config_section)

    def included_config_scopes(self):
        """List of included configuration scopes from the environment.

        Scopes are listed in the YAML file in order from highest to
        lowest precedence, so configuration from earlier scope will take
        precedence over later ones.

        This routine returns them in the order they should be pushed onto
        the internal scope stack (so, in reverse, from lowest to highest).
        """
        scopes = []

        # load config scopes added via 'include:', in reverse so that
        # highest-precedence scopes are last.
        includes = config_dict(self.config_sections["workspace"]["yaml"]).get("include", [])
        missing = []
        for full_config_path in reversed(includes):
            # Remove trailing slash
            config_path = full_config_path
            if full_config_path.endswith("/"):
                config_path = full_config_path[:-1]

            # allow paths to contain ramble config/environment variables, etc.
            config_path = substitute_path_variables(
                config_path, local_replacements=self.workspace_paths()
            )

            # treat relative paths as relative to the environment
            if not os.path.isabs(config_path):
                config_path = os.path.join(self.path, config_path)
                config_path = os.path.normpath(os.path.realpath(config_path))

            if os.path.isdir(config_path):
                # directories are treated as regular ConfigScopes
                config_name = f"workspace:{self.name}:{os.path.basename(config_path)}"
                scope = ramble.config.ConfigScope(config_name, config_path)
            elif os.path.exists(config_path):
                # files are assumed to be SingleFileScopes
                config_name = f"workspace:{self.name}:{config_path}"
                scope = ramble.config.SingleFileScope(
                    config_name, config_path, ramble.schema.merged.schema
                )
            else:
                missing.append(config_path)
                continue

            scopes.append(scope)

        if missing:
            msg = f"Detected {len(missing)} missing include path(s):"
            msg += "\n   {}".format("\n   ".join(missing))
            logger.die(f"{msg}\nPlease correct and try again.")

        return scopes

    def ws_file_config_scope_name(self):
        """Name of the config scope of this workspace's config file."""
        return f"workspace:{self.name}:{self.config_dir}"
        # return 'ws:%s' % self.name

    def ws_file_config_scope(self):
        """Get the configuration scope for the workspace's config file."""
        section = self.config_sections["workspace"]
        config_name = self.ws_file_config_scope_name()
        return ramble.config.SingleFileScope(
            config_name,
            section["path"],
            ramble.schema.workspace.schema,
            [ramble.config.first_existing(section["raw_yaml"], ramble.schema.workspace.keys)],
        )

    def config_scopes(self):
        """A list of all configuration scopes for this workspace."""
        return self.included_config_scopes() + [self.ws_file_config_scope()] + [self.configs]

    def destroy(self):
        """Remove this workspace from Ramble entirely."""
        shutil.rmtree(self.path)

    def _get_workspace_dict(self):
        return (
            self.config_sections["workspace"]["yaml"]
            if "workspace" in self.config_sections
            else None
        )

    def _get_application_dict_config(self, key):
        return self.application_configs[key]["yaml"] if key in self.application_configs else None

    def _get_workspace_section(self, section):
        """Return a dict of a workspace section"""
        workspace_dict = self._get_workspace_dict()

        return (
            workspace_dict[namespace.ramble][section]
            if section in workspace_dict[namespace.ramble]
            else syaml.syaml_dict()
        )

    def get_workspace_vars(self):
        """Return a dict of workspace variables"""
        return ramble.config.config.get_config("variables")

    def get_workspace_env_vars(self):
        """Return a dict of workspace environment variables"""
        return ramble.config.config.get_config("env_vars")

    def get_workspace_formatted_executables(self):
        """Return a dict of workspace formatted executables"""
        return ramble.config.config.get_config("formatted_executables")

    def get_workspace_internals(self):
        """Return a dict of workspace internals"""
        return ramble.config.config.get_config(namespace.internals)

    def get_workspace_modifiers(self):
        """Return a dict of workspace modifiers"""
        return ramble.config.config.get_config("modifiers")

    def get_workspace_zips(self):
        """Return a dict of workspace zips"""
        return ramble.config.config.get_config("zips")

    def get_workspace_variants(self):
        """Return a dict of workspace variants"""
        return ramble.config.config.get_config("variants")

    def get_software_dict(self):
        """Return the software dictionary for this workspace"""
        # DEPRECATED: Remove once the spack config section is completely removed
        spack_dict = ramble.config.config.get_config("spack")
        software_dict = ramble.config.config.get_config(namespace.software)

        if spack_dict:
            logger.die(
                "The spack configuration section is deprecated. "
                "Please update to the software dict."
            )

        if namespace.packages in software_dict:
            for pkg, config in software_dict[namespace.packages].items():
                if "spack_spec" in config:
                    logger.die(
                        f'Package {pkg} defines "spack_spec" which is deprecated. '
                        'Convert this to "pkg_spec" or "spack_pkg_spec" instead.'
                    )

        return software_dict

    def get_applications(self):
        """Get the dictionary of applications"""
        logger.debug("Getting app dict.")
        logger.debug(f" {self._get_workspace_dict()}")
        workspace_dict = self._get_workspace_dict()
        if namespace.application not in workspace_dict[namespace.ramble]:
            workspace_dict[namespace.ramble][namespace.application] = syaml.syaml_dict()
        return workspace_dict[namespace.ramble][namespace.application]

    def read_transaction(self):
        """Get a read lock context manager for use in a `with` block."""
        return lk.ReadTransaction(self.txlock, acquire=self._re_read)

    def write_transaction(self):
        """Get a write lock context manager for use in a `with` block."""
        return lk.WriteTransaction(self.txlock, acquire=self._re_read)

    def __enter__(self):
        self._previous_active = _active_workspace
        activate(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        deactivate()
        if self._previous_active:
            activate(self._previous_active)

    def check_cache(self, tupl):
        return self.install_cache.contains(tupl)

    def add_to_cache(self, tupl):
        self.install_cache.add(tupl)


def read(name):
    """Get a workspace with the supplied name."""
    validate_workspace_name(name)
    if not exists(name):
        raise RambleWorkspaceError("no such workspace '%s'" % name)
    return Workspace(root(name))


def yaml_equivalent(first, second):
    """Returns whether two ramble yaml items are equivalent, including overrides"""
    if isinstance(first, dict):
        return isinstance(second, dict) and _equiv_dict(first, second)
    elif isinstance(first, list):
        return isinstance(second, list) and _equiv_list(first, second)
    else:  # it's a string
        return isinstance(second, str) and first == second


def _equiv_list(first, second):
    """Returns whether two ramble yaml lists are equivalent, including overrides"""
    if len(first) != len(second):
        return False
    return all(yaml_equivalent(f, s) for f, s in zip(first, second))


def _equiv_dict(first, second):
    """Returns whether two ramble yaml dicts are equivalent, including overrides"""
    if len(first) != len(second):
        return False
    same_values = all(yaml_equivalent(fv, sv) for fv, sv in zip(first.values(), second.values()))
    same_keys_with_same_overrides = all(
        fk == sk and getattr(fk, "override", False) == getattr(sk, "override", False)
        for fk, sk in zip(first.keys(), second.keys())
    )
    return same_values and same_keys_with_same_overrides


def _read_yaml(str_or_file, schema):
    """Read YAML from a file for round-trip parsing."""
    data = syaml.load_config(str_or_file)
    filename = getattr(str_or_file, "name", None)
    default_data = ramble.config.validate(data, schema, filename)
    return (data, default_data)


def _write_yaml(data, str_or_file, schema):
    """Write YAML to a file preserving comments and dict order."""
    filename = getattr(str_or_file, "name", None)
    ramble.config.validate(data, schema, filename)
    syaml.dump_config(data, str_or_file, default_flow_style=False)


@contextlib.contextmanager
def no_active_workspace():
    """Deactivate the active workspace for the duration of the context. Has no
    effect when there is no active workspace."""
    ws = active_workspace()
    env_var = None
    if ramble_workspace_var in os.environ.keys():
        env_var = os.environ[ramble_workspace_var]
        del os.environ[ramble_workspace_var]

    try:
        deactivate()
        yield
    finally:
        if ws:
            os.environ[ramble_workspace_var] = env_var
            activate(ws)


def _filter_results(results, summary_only):
    if not summary_only or "experiments" not in results:
        return results
    results = copy.deepcopy(results)
    results["experiments"] = [r for r in results["experiments"] if r["N_REPEATS"] > 0]
    return results


class RambleWorkspaceError(ramble.error.RambleError):
    """Superclass for all errors to do with Ramble Workspaces"""


class RambleInvalidTemplateNameError(ramble.error.RambleError):
    """Error when an invalid template name is provided"""


class RambleConflictingDefinitionError(RambleWorkspaceError):
    """Error when conflicting software definitions are found"""


class RambleActiveWorkspaceError(RambleWorkspaceError):
    """Error when an invalid workspace is activated"""


class RambleMissingApplicationError(RambleWorkspaceError):
    """Error when using an undefined application in an experiment
    specification"""


class RambleMissingWorkloadError(RambleWorkspaceError):
    """Error when using an undefined workload in an experiment
    specification"""


class RambleMissingExperimentError(RambleWorkspaceError):
    """Error when using an undefined experiment in an experiment
    specification"""


class RambleMissingApplicationDirError(RambleWorkspaceError):
    """Error when using a non-existent application directory"""
