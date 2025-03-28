# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import sys
import tempfile

import llnl.util.tty as tty
import llnl.util.tty.color as color
from llnl.util.tty.colify import colify, colified

import spack.util.string as string
from spack.util.editor import editor
import spack.util.environment

import ramble.cmd
import ramble.cmd.common.arguments
import ramble.cmd.common.arguments as arguments

import ramble.config
import ramble.workspace
import ramble.workspace.shell
import ramble.expander
import ramble.experiment_set
import ramble.context
import ramble.pipeline
import ramble.filters
import ramble.experimental.uploader
import ramble.software_environments
import ramble.util.colors as rucolor
from ramble.util.logger import logger
from ramble.namespace import namespace


description = "manage experiment workspaces"
section = "workspaces"
level = "short"

subcommands = [
    "activate",
    "archive",
    "deactivate",
    "create",
    "concretize",
    "setup",
    "analyze",
    "push-to-cache",
    "info",
    "edit",
    "mirror",
    "experiment-logs",
    ["list", "ls"],
    ["remove", "rm"],
    "generate-config",
    "manage",
]

manage_commands = ["experiments", "software", "includes"]


def workspace_activate_setup_parser(subparser):
    """Set the current workspace"""
    shells = subparser.add_mutually_exclusive_group()
    shells.add_argument(
        "--sh",
        action="store_const",
        dest="shell",
        const="sh",
        help="print sh commands to activate the workspace",
    )
    shells.add_argument(
        "--csh",
        action="store_const",
        dest="shell",
        const="csh",
        help="print csh commands to activate the workspace",
    )
    shells.add_argument(
        "--fish",
        action="store_const",
        dest="shell",
        const="fish",
        help="print fish commands to activate the workspace",
    )
    shells.add_argument(
        "--bat",
        action="store_const",
        dest="shell",
        const="bat",
        help="print bat commands to activate the environment",
    )

    subparser.add_argument(
        "-p",
        "--prompt",
        action="store_true",
        default=False,
        help="decorate the command line prompt when activating",
    )

    ws_options = subparser.add_mutually_exclusive_group()
    ws_options.add_argument(
        "--temp",
        action="store_true",
        default=False,
        help="create and activate a workspace in a temporary directory",
    )
    ws_options.add_argument(
        "-d", "--dir", default=None, help="activate the workspace in this directory"
    )
    ws_options.add_argument(
        metavar="workspace",
        dest="activate_workspace",
        nargs="?",
        default=None,
        help="name of workspace to activate",
    )


def create_temp_workspace_directory():
    """
    Returns the path of a temporary directory in which to
    create a workspace
    """
    return tempfile.mkdtemp(prefix="ramble-")


def workspace_activate(args):
    if not args.activate_workspace and not args.dir and not args.temp:
        logger.die("ramble workspace activate requires a workspace name, directory, or --temp")

    if not args.shell:
        ramble.cmd.common.shell_init_instructions(
            "ramble workspace activate", "    eval `ramble workspace activate {sh_arg} [...]`"
        )
        return 1

    workspace_name_or_dir = args.activate_workspace or args.dir

    # Temporary workspace
    if args.temp:
        workspace = create_temp_workspace_directory()
        workspace_path = os.path.abspath(workspace)
        short_name = os.path.basename(workspace_path)
        ramble.workspace.Workspace(workspace).write()

    # Named workspace
    elif ramble.workspace.exists(workspace_name_or_dir) and not args.dir:
        workspace_path = ramble.workspace.root(workspace_name_or_dir)
        short_name = workspace_name_or_dir

    # Workspace directory
    elif ramble.workspace.is_workspace_dir(workspace_name_or_dir):
        workspace_path = os.path.abspath(workspace_name_or_dir)
        short_name = os.path.basename(workspace_path)

    else:
        logger.die(f"No such workspace: '{workspace_name_or_dir}'")

    workspace_prompt = "[%s]" % short_name

    # We only support one active workspace at a time, so deactivate the current one.
    if ramble.workspace.active_workspace() is None:
        cmds = ""
        env_mods = spack.util.environment.EnvironmentModifications()
    else:
        cmds = ramble.workspace.shell.deactivate_header(shell=args.shell)
        env_mods = ramble.workspace.shell.deactivate()

    # Activate new workspace
    active_workspace = ramble.workspace.Workspace(workspace_path)
    cmds += ramble.workspace.shell.activate_header(
        ws=active_workspace, shell=args.shell, prompt=workspace_prompt if args.prompt else None
    )
    env_mods.extend(ramble.workspace.shell.activate(ws=active_workspace))
    cmds += env_mods.shell_modifications(args.shell)
    sys.stdout.write(cmds)


def workspace_deactivate_setup_parser(subparser):
    """deactivate any active workspace in the shell"""
    shells = subparser.add_mutually_exclusive_group()
    shells.add_argument(
        "--sh",
        action="store_const",
        dest="shell",
        const="sh",
        help="print sh commands to deactivate the workspace",
    )
    shells.add_argument(
        "--csh",
        action="store_const",
        dest="shell",
        const="csh",
        help="print csh commands to deactivate the workspace",
    )
    shells.add_argument(
        "--fish",
        action="store_const",
        dest="shell",
        const="fish",
        help="print fish commands to activate the workspace",
    )
    shells.add_argument(
        "--bat",
        action="store_const",
        dest="shell",
        const="bat",
        help="print bat commands to activate the environment",
    )


def workspace_deactivate(args):
    if not args.shell:
        ramble.cmd.common.shell_init_instructions(
            "ramble workspace deactivate",
            "    eval `ramble workspace deactivate {sh_arg}`",
        )
        return 1

    # Error out when -w, -W, -D flags are given, cause they are ambiguous.
    if args.workspace or args.no_workspace or args.workspace_dir:
        logger.die(
            "Calling ramble workspace deactivate with --workspace,"
            " --workspace-dir, and --no-workspace "
            "is ambiguous"
        )

    if ramble.workspace.active_workspace() is None:
        if ramble.workspace.ramble_workspace_var not in os.environ:
            logger.die("No workspace is currently active.")

    cmds = ramble.workspace.shell.deactivate_header(args.shell)
    env_mods = ramble.workspace.shell.deactivate()
    cmds += env_mods.shell_modifications(args.shell)
    sys.stdout.write(cmds)


def workspace_create_setup_parser(subparser):
    """create a new workspace"""
    subparser.add_argument(
        "create_workspace", metavar="wrkspc", help="name of workspace to create"
    )
    subparser.add_argument("-c", "--config", help="configuration file to create workspace with")
    subparser.add_argument(
        "-t", "--template_execute", help="execution template file to use when creating workspace"
    )
    subparser.add_argument(
        "-d", "--dir", action="store_true", help="create a workspace in a specific directory"
    )
    subparser.add_argument(
        "--software-dir",
        metavar="dir",
        help="external directory to link as software directory in workspace",
    )
    subparser.add_argument(
        "--inputs-dir",
        metavar="dir",
        help="external directory to link as inputs directory in workspace",
    )
    subparser.add_argument(
        "-a",
        "--activate",
        action="store_true",
        help="activate the created workspace, if specified. Default is false",
    )


def workspace_create(args):
    _workspace_create(
        args.create_workspace,
        args.dir,
        args.config,
        args.template_execute,
        software_dir=args.software_dir,
        inputs_dir=args.inputs_dir,
        activate=args.activate,
    )


def _workspace_create(
    name_or_path,
    dir=False,
    config=None,
    template_execute=None,
    software_dir=None,
    inputs_dir=None,
    activate=False,
):
    """Create a new workspace

    Arguments:
        name_or_path (str): name of the workspace to create, or path
                            to it
        dir (bool): if True, create a workspace in a directory instead
            of a named workspace
        config (str): path to a configuration file that should
                      generate the workspace
        template_execute (str): Path to a template execute script to
                                create the workspace with
        software_dir (str): Path to software dir that should be linked
                            instead of creating a new directory.
        inputs_dir (str): Path to inputs dir that should be linked
                          instead of creating a new directory.
        activate (bool): if True, activate the created workspace. Default is False.
    """

    # Sanity check file paths, to avoid half-creating an incomplete workspace
    for filepath in [config, template_execute]:
        if filepath and not os.path.isfile(filepath):
            logger.die(f"{filepath} file path invalid")

    read_default_template = True

    # Disallow generation of default template when both a config and a template
    # are specified
    if config and template_execute:
        read_default_template = False

    if dir:
        workspace = ramble.workspace.Workspace(
            name_or_path, read_default_template=read_default_template
        )
        ws_loc = workspace.path

    else:
        workspace = ramble.workspace.create(
            name_or_path, read_default_template=read_default_template
        )

        workspace.read_default_template = read_default_template
        ws_loc = name_or_path

    activate_cmd = f"ramble workspace activate {ws_loc}"
    if not activate:
        logger.msg(f"Created workspace in {ws_loc}")
        logger.msg("You can activate this workspace with:")
        logger.msg(f"  {activate_cmd}")

    workspace.write(inputs_dir=inputs_dir, software_dir=software_dir)

    if config:
        with open(config) as f:
            workspace._read_config("workspace", f)
            workspace._write_config("workspace", force=True)

    if template_execute:
        with open(template_execute) as f:
            _, file_name = os.path.split(template_execute)
            template_name = os.path.splitext(file_name)[0]
            workspace._read_template(template_name, f.read())
            workspace._write_templates()

    if activate:
        sys.stdout.write(activate_cmd)
    return workspace


def workspace_remove_setup_parser(subparser):
    """remove an existing workspace"""
    subparser.add_argument(
        "rm_wrkspc", metavar="workspace", nargs="+", help="workspace(s) to remove"
    )
    arguments.add_common_arguments(subparser, ["yes_to_all"])


def workspace_remove(args):
    """Remove a *named* workspace.

    This removes an environment managed by Ramble. Directory workspaces
    should be removed manually.
    """
    read_workspaces = []
    for workspace_name in args.rm_wrkspc:
        workspace = ramble.workspace.read(workspace_name)
        read_workspaces.append(workspace)

    logger.debug(f"Removal args: {args}")

    if not args.yes_to_all:
        answer = tty.get_yes_or_no(
            "Really remove %s %s?"
            % (
                string.plural(len(args.rm_wrkspc), "workspace", show_n=False),
                string.comma_and(args.rm_wrkspc),
            ),
            default=False,
        )
        if not answer:
            logger.die("Will not remove any workspaces")

    for workspace in read_workspaces:
        if workspace.active:
            logger.die(f"Workspace {workspace.name} can't be removed while activated.")

        workspace.destroy()
        logger.msg(f"Successfully removed workspace '{workspace.name}'")


def workspace_concretize_setup_parser(subparser):
    """Concretize a workspace"""
    subparser.add_argument(
        "-f",
        "--force-concretize",
        dest="force_concretize",
        action="store_true",
        help="Overwrite software environment configuration with defaults defined in application "
        + "definition",
        required=False,
    )
    subparser.add_argument(
        "--simplify",
        dest="simplify",
        action="store_true",
        help="Remove unused software and experiment templates from workspace config",
        required=False,
    )
    subparser.add_argument(
        "--quiet",
        "-q",
        dest="quiet",
        action="store_true",
        help="Silently ignore conflicting package definitions",
        required=False,
    )


def workspace_concretize(args):
    ws = ramble.cmd.require_active_workspace(cmd_name="workspace concretize")

    if args.simplify:
        logger.debug("Simplifying workspace config")
        ws.simplify()
    else:
        logger.debug("Concretizing workspace")
        ws.concretize(force=args.force_concretize, quiet=args.quiet)


def workspace_run_pipeline(args, pipeline):
    include_phase_dependencies = getattr(args, "include_phase_dependencies", None)
    if include_phase_dependencies:
        with ramble.config.override("config:include_phase_dependencies", True):
            pipeline.run()
    else:
        pipeline.run()


def workspace_setup_setup_parser(subparser):
    """Setup a workspace"""
    subparser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="perform a dry run. Sets up directories and generates "
        + "all scripts. Prints commands that would be executed "
        + "for installation, and files that would be downloaded.",
    )

    arguments.add_common_arguments(
        subparser,
        ["phases", "include_phase_dependencies", "where", "exclude_where", "filter_tags"],
    )


def workspace_setup(args):
    current_pipeline = ramble.pipeline.pipelines.setup
    ws = ramble.cmd.require_active_workspace(cmd_name="workspace setup")

    if args.dry_run:
        ws.dry_run = True

    filters = ramble.filters.Filters(
        phase_filters=args.phases,
        include_where_filters=args.where,
        exclude_where_filters=args.exclude_where,
        tags=args.filter_tags,
    )

    pipeline_cls = ramble.pipeline.pipeline_class(current_pipeline)

    logger.debug("Setting up workspace")
    pipeline = pipeline_cls(ws, filters)

    with ws.read_transaction():
        workspace_run_pipeline(args, pipeline)


def workspace_analyze_setup_parser(subparser):
    """Analyze a workspace"""
    subparser.add_argument(
        "-f",
        "--formats",
        dest="output_formats",
        nargs="+",
        default=["text"],
        help="list of output formats to write." + "Supported formats are json, yaml, or text",
        required=False,
    )

    subparser.add_argument(
        "-u",
        "--upload",
        dest="upload",
        action="store_true",
        help="Push experiment data to remote store (as defined in config)",
        required=False,
    )

    subparser.add_argument(
        "-p",
        "--print-results",
        dest="print_results",
        action="store_true",
        help="print out the analysis result",
    )

    subparser.add_argument(
        "-s",
        "--summary-only",
        dest="summary_only",
        action="store_true",
        help="print out only the summary stats for repeated experiments",
    )

    arguments.add_common_arguments(
        subparser,
        ["phases", "include_phase_dependencies", "where", "exclude_where", "filter_tags"],
    )


def workspace_analyze(args):
    current_pipeline = ramble.pipeline.pipelines.analyze
    ws = ramble.cmd.require_active_workspace(cmd_name="workspace analyze")
    ws.repeat_success_strict = ramble.config.get("config:repeat_success_strict")

    filters = ramble.filters.Filters(
        phase_filters=args.phases,
        include_where_filters=args.where,
        exclude_where_filters=args.exclude_where,
        tags=args.filter_tags,
    )

    pipeline_cls = ramble.pipeline.pipeline_class(current_pipeline)

    logger.debug("Analyzing workspace")
    pipeline = pipeline_cls(
        ws,
        filters,
        output_formats=args.output_formats,
        upload=args.upload,
        print_results=args.print_results,
        summary_only=args.summary_only,
    )

    with ws.read_transaction():
        workspace_run_pipeline(args, pipeline)


def workspace_push_to_cache(args):
    current_pipeline = ramble.pipeline.pipelines.pushtocache
    ws = ramble.cmd.require_active_workspace(cmd_name="workspace pushtocache")

    filters = ramble.filters.Filters(
        phase_filters="*",
        include_where_filters=args.where,
        exclude_where_filters=args.exclude_where,
        tags=args.filter_tags,
    )
    pipeline_cls = ramble.pipeline.pipeline_class(current_pipeline)

    pipeline = pipeline_cls(ws, filters, spack_cache_path=args.cache_path)

    workspace_run_pipeline(args, pipeline)
    pipeline.run()


def workspace_push_to_cache_setup_parser(subparser):
    """push workspace envs to a given buildcache"""

    subparser.add_argument(
        "-d", dest="cache_path", default=None, required=True, help="Path to cache."
    )

    arguments.add_common_arguments(subparser, ["where", "exclude_where", "filter_tags"])


def workspace_info_setup_parser(subparser):
    """Information about a workspace"""
    software_opts = subparser.add_mutually_exclusive_group()
    software_opts.add_argument(
        "--software",
        action="store_true",
        help="If set, used software stack information will be printed",
    )

    software_opts.add_argument(
        "--all-software",
        action="store_true",
        help="If set, all software stack information will be printed",
    )

    subparser.add_argument(
        "--templates", action="store_true", help="If set, workspace templates will be printed"
    )

    subparser.add_argument(
        "--expansions", action="store_true", help="If set, variable expansions will be printed"
    )

    subparser.add_argument(
        "--tags", action="store_true", help="If set, experiment tags will be printed"
    )

    subparser.add_argument(
        "--phases", action="store_true", help="If set, phase information will be printed"
    )

    arguments.add_common_arguments(subparser, ["where", "exclude_where", "filter_tags"])

    subparser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="level of verbosity. Add flags to "
        + "increase description of workspace\n"
        + "level 1 enables software, tags, and templates\n"
        + "level 2 enables expansions and phases\n",
    )


def workspace_info(args):
    ws = ramble.cmd.require_active_workspace(cmd_name="workspace info")

    # Enable verbose mode
    if args.verbose >= 1:
        args.software = True
        args.tags = True
        args.templates = True

    if args.verbose >= 2:
        args.expansions = True
        args.phases = True

    color.cprint(rucolor.section_title("Workspace: ") + ws.name)
    color.cprint("")
    color.cprint(rucolor.section_title("Location: ") + ws.path)

    # Print workspace templates that currently exist
    if args.templates:
        color.cprint("")
        color.cprint(rucolor.section_title("Workspace Templates:"))
        for template, _ in ws.all_templates():
            color.cprint("    %s" % template)

    # Print workspace variables information
    workspace_vars = ws.get_workspace_vars()

    ws.software_environments = ramble.software_environments.SoftwareEnvironments(ws)
    software_environments = ws.software_environments

    # Build experiment set
    experiment_set = ws.build_experiment_set()

    if args.tags:
        color.cprint("")
        all_tags = experiment_set.all_experiment_tags()
        color.cprint(rucolor.section_title("All experiment tags:"))
        color.cprint(colified(all_tags, indent=4))

    # Print experiment information
    # We built a "print_experiment_set" to access the scopes of variables for each
    # experiment, rather than having merged scopes as we do in the base experiment_set.
    # The base experiment_set is used to list *all* experiments.
    all_pipelines = {}
    color.cprint("")
    color.cprint(rucolor.section_title("Experiments:"))
    for workloads, application_context in ws.all_applications():
        for experiments, workload_context in ws.all_workloads(workloads):
            for _, experiment_context in ws.all_experiments(experiments):
                print_experiment_set = ramble.experiment_set.ExperimentSet(ws)
                print_experiment_set.set_application_context(application_context)
                print_experiment_set.set_workload_context(workload_context)
                print_experiment_set.set_experiment_context(experiment_context)
                print_experiment_set.build_experiment_chains()

                # Reindex the experiments in the print set to match the overall set
                for exp_name, print_app_inst, _ in print_experiment_set.all_experiments():
                    app_inst = experiment_set.get_experiment(exp_name)
                    experiment_index = app_inst.expander.expand_var_name(
                        app_inst.keywords.experiment_index
                    )

                    print_app_inst.define_variable(
                        print_app_inst.keywords.experiment_index, experiment_index
                    )

                print_header = True
                # Define variable printing groups.
                var_indent = "        "
                var_group_names = [
                    rucolor.config_title("Config"),
                    rucolor.section_title("Workspace"),
                    rucolor.nested_1("Application"),
                    rucolor.nested_2("Workload"),
                    rucolor.nested_3("Experiment"),
                ]
                header_base = rucolor.nested_4("Variables from")
                config_vars = ramble.config.config.get("config:variables")

                # Construct filters here...
                filters = ramble.filters.Filters(
                    phase_filters=[],
                    include_where_filters=args.where,
                    exclude_where_filters=args.exclude_where,
                    tags=args.filter_tags,
                )

                for exp_name, _, _ in print_experiment_set.filtered_experiments(filters):
                    app_inst = experiment_set.get_experiment(exp_name)
                    if app_inst.package_manager is not None:
                        software_environments.render_environment(
                            app_inst.expander.expand_var("{env_name}"),
                            app_inst.expander,
                            app_inst.package_manager,
                        )
                        # Track this env as used, for printing purposes
                        software_environments.use_environment(
                            app_inst.package_manager, app_inst.expander.expand_var("{env_name}")
                        )

                    if print_header:
                        color.cprint(
                            rucolor.nested_1("  Application: ") + application_context.context_name
                        )
                        color.cprint(
                            rucolor.nested_2("    Workload: ") + workload_context.context_name
                        )
                        print_header = False

                    # Aggregate pipeline phases
                    for pipeline in app_inst._pipelines:
                        if pipeline not in all_pipelines:
                            all_pipelines[pipeline] = set()
                        for phase in app_inst.get_pipeline_phases(pipeline):
                            all_pipelines[pipeline].add(phase)

                    experiment_index = app_inst.expander.expand_var_name(
                        app_inst.keywords.experiment_index
                    )

                    if app_inst.is_template:
                        color.cprint(
                            rucolor.nested_3(f"      Template Experiment {experiment_index}: ")
                            + exp_name
                        )
                    elif app_inst.repeats.is_repeat_base:
                        color.cprint(
                            rucolor.nested_3(f"      Repeat Base Experiment {experiment_index}: ")
                            + exp_name
                        )
                    else:
                        color.cprint(
                            rucolor.nested_3(f"      Experiment {experiment_index}: ") + exp_name
                        )

                    if args.tags:
                        color.cprint("        Experiment Tags: " + str(app_inst.experiment_tags))

                    if args.expansions:
                        var_groups = [
                            config_vars,
                            workspace_vars,
                            application_context.variables,
                            workload_context.variables,
                            experiment_context.variables,
                        ]

                        # Print each group that has variables in it
                        for group, name in zip(var_groups, var_group_names):
                            if group:
                                header = f"{header_base} {name}"
                                app_inst.print_vars(
                                    header=header, vars_to_print=group, indent=var_indent
                                )

                        app_inst.print_internals(indent=var_indent)
                        app_inst.print_chain_order(indent=var_indent)

    if args.phases:
        for pipeline in sorted(all_pipelines.keys()):
            color.cprint("")
            color.cprint(rucolor.section_title(f"Phases for {pipeline} pipeline:"))
            colify(all_pipelines[pipeline], indent=4)

    # Print software stack information
    if args.software or args.all_software:
        color.cprint("")
        color.cprint(rucolor.section_title("Software Stack:"))
        only_used_software = args.software
        color.cprint(
            software_environments.info(
                verbosity=args.verbose, indent=4, color_level=1, only_used=only_used_software
            )
        )


#
# workspace list
#


def workspace_list_setup_parser(subparser):
    """list available workspaces"""
    pass


def workspace_list(args):
    names = ramble.workspace.all_workspace_names()

    color_names = []
    for name in names:
        if ramble.workspace.active(name):
            name = color.colorize("@*g{%s}" % name)
        color_names.append(name)

    # say how many there are if writing to a tty
    if sys.stdout.isatty():
        if not names:
            logger.msg("No workspaces")
        else:
            logger.msg(f"{len(names)} workspaces")

    colify(color_names, indent=4)


def workspace_edit_setup_parser(subparser):
    """edit workspace config or template"""
    subparser.add_argument(
        "-f",
        "--file",
        dest="filename",
        default=None,
        help="Open a single file by filename",
        required=False,
    )

    subparser.add_argument(
        "-c",
        "--config_only",
        dest="config_only",
        action="store_true",
        help="Only open config files",
        required=False,
    )

    subparser.add_argument(
        "-t",
        "--template_only",
        dest="template_only",
        action="store_true",
        help="Only open template files",
        required=False,
    )

    subparser.add_argument(
        "-l",
        "--license_only",
        dest="license_only",
        action="store_true",
        help="Only open license config files",
        required=False,
    )

    subparser.add_argument(
        "--all",
        dest="all_files",
        action="store_true",
        help="Open all yaml and template files in workspace config directory",
        required=False,
    )

    subparser.add_argument(
        "-p", "--print-file", action="store_true", help="print the file name that would be edited"
    )


def workspace_edit(args):
    ramble_ws = ramble.cmd.find_workspace_path(args)

    if not ramble_ws:
        logger.die(
            "ramble workspace edit requires either a command "
            "line workspace or an active workspace"
        )

    config_file = ramble.workspace.config_file(ramble_ws)
    template_files = ramble.workspace.all_template_paths(ramble_ws)

    edit_files = [config_file]
    edit_files.extend(template_files)

    if args.filename:
        expander = ramble.expander.Expander(
            ramble.workspace.Workspace.get_workspace_paths(ramble_ws), None
        )
        # If filename contains expansion strings, edit expanded path. Else assume configs dir.
        expanded_filename = expander.expand_var(args.filename)
        if expanded_filename != args.filename:
            edit_files = [expanded_filename]
        else:
            edit_files = [ramble.workspace.get_filepath(ramble_ws, expanded_filename)]
    elif args.config_only:
        edit_files = [config_file]
    elif args.template_only:
        edit_files = template_files
    elif args.license_only:
        licenses_file = [ramble.workspace.licenses_file(ramble_ws)]
        edit_files = licenses_file
    elif args.all_files:
        edit_files = ramble.workspace.all_config_files(ramble_ws) + template_files

    if args.print_file:
        for f in edit_files:
            print(f)
    else:
        try:
            editor(*edit_files)
        except TypeError:
            logger.die("No valid editor was found.")


def workspace_archive_setup_parser(subparser):
    """archive current workspace state"""
    subparser.add_argument(
        "--tar-archive",
        "-t",
        action="store_true",
        dest="tar_archive",
        help="create a tar.gz of the archive directory for backing up.",
    )

    subparser.add_argument(
        "--prefix",
        "-p",
        dest="archive_prefix",
        default=None,
        help="Specify archive prefix to customize output filename.",
    )

    subparser.add_argument(
        "--upload-url",
        "-u",
        dest="upload_url",
        default=None,
        help="URL to upload tar archive into. Does nothing if `-t` is not specified.",
    )

    subparser.add_argument(
        "--include-secrets",
        action="store_true",
        help="If set, secrets are included in the archive. Default is false",
    )

    arguments.add_common_arguments(
        subparser, ["phases", "include_phase_dependencies", "where", "exclude_where"]
    )


def workspace_archive(args):
    current_pipeline = ramble.pipeline.pipelines.archive
    ws = ramble.cmd.require_active_workspace(cmd_name="workspace archive")

    filters = ramble.filters.Filters(
        phase_filters=args.phases,
        include_where_filters=args.where,
        exclude_where_filters=args.exclude_where,
    )

    pipeline_cls = ramble.pipeline.pipeline_class(current_pipeline)
    pipeline = pipeline_cls(
        ws,
        filters,
        create_tar=args.tar_archive,
        archive_prefix=args.archive_prefix,
        upload_url=args.upload_url,
        include_secrets=args.include_secrets,
    )

    workspace_run_pipeline(args, pipeline)


def workspace_mirror_setup_parser(subparser):
    """mirror current workspace state"""
    subparser.add_argument(
        "-d", dest="mirror_path", default=None, required=True, help="Path to create mirror in."
    )

    subparser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="perform a dry run. Creates package environments, "
        + "prints package manager specific commands that would be executed "
        + "for creating the mirror.",
    )

    arguments.add_common_arguments(
        subparser, ["phases", "include_phase_dependencies", "where", "exclude_where"]
    )


def workspace_mirror(args):
    current_pipeline = ramble.pipeline.pipelines.mirror
    ws = ramble.cmd.require_active_workspace(cmd_name="workspace archive")

    if args.dry_run:
        ws.dry_run = True

    filters = ramble.filters.Filters(
        phase_filters=args.phases,
        include_where_filters=args.where,
        exclude_where_filters=args.exclude_where,
    )
    pipeline_cls = ramble.pipeline.pipeline_class(current_pipeline)

    pipeline = pipeline_cls(ws, filters, mirror_path=args.mirror_path)

    workspace_run_pipeline(args, pipeline)
    pipeline.run()


def workspace_manage_experiments_setup_parser(subparser):
    """manage experiment definitions"""
    arguments.add_common_arguments(subparser, ["application"])

    subparser.add_argument(
        "--workload-filter",
        "--wf",
        dest="workload_filters",
        action="append",
        help="glob filter to use when selecting workloads in the application. "
        + "Workload is kept if it matches any filter.",
    )

    subparser.add_argument(
        "--variable-filter",
        "--vf",
        dest="variable_filters",
        action="append",
        help="glob filter to use when selecting variables in the workloads. "
        + "Variable is kept if it matches any filter.",
    )

    subparser.add_argument(
        "--variable-definition",
        "-v",
        dest="variable_definitions",
        action="append",
        help="variable definition to set in the generated experiments. "
        + "Given in the form key=value",
    )

    subparser.add_argument(
        "--experiment-name",
        "-e",
        dest="experiment_name",
        default="generated",
        help="name of generated experiment",
    )

    subparser.add_argument(
        "--package-manager",
        "-p",
        dest="package_manager",
        default=None,
        help="name of (optional) package to define within the experiment scope",
    )

    subparser.add_argument(
        "--dry-run",
        "--print",
        dest="dry_run",
        action="store_true",
        help="perform a dry run. Print resulting config to screen and not "
        + "to the workspace configuration file",
    )

    subparser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        help="overwrite existing definitions with newly generated definitions",
    )

    variable_control = subparser.add_mutually_exclusive_group()
    variable_control.add_argument(
        "--include-default-variables",
        "-i",
        action="store_true",
        help="whether to include default variable values in the resulting config",
    )

    variable_control.add_argument(
        "--workload-name-variable",
        "-w",
        default=None,
        metavar="VAR",
        help="variable name to collapse workloads in",
    )

    subparser.add_argument(
        "--zip",
        "-z",
        dest="zips",
        action="append",
        help="zip to define for the experiments, in the format zipname=[zipvar1,zipvar2]",
    )

    subparser.add_argument(
        "--matrix",
        "-m",
        dest="matrix",
        help="comma delimited list of variable names to matrix in the experiments",
    )


def workspace_manage_experiments(args):
    """Perform experiment management"""
    ws = ramble.cmd.find_workspace(args)

    if ws is None:
        import tempfile

        logger.warn("No active workspace found. Defaulting to `--dry-run`")

        root = tempfile.TemporaryDirectory()
        ws = ramble.workspace.Workspace(str(root))
        ws.dry_run = True
    else:
        ws.dry_run = args.dry_run

    workload_filters = ["*"]
    if args.workload_filters:
        workload_filters = args.workload_filters

    variable_filters = ["*"]
    if args.variable_filters:
        variable_filters = args.variable_filters

    variable_definitions = []
    if args.variable_definitions:
        variable_definitions = args.variable_definitions

    zips = []
    if args.zips:
        zips = args.zips

    matrix = None
    if args.matrix:
        matrix = args.matrix

    ws.add_experiments(
        args.application,
        args.workload_name_variable,
        workload_filters,
        args.include_default_variables,
        variable_filters,
        variable_definitions,
        args.experiment_name,
        args.package_manager,
        zips,
        matrix,
        args.overwrite,
    )

    if ws.dry_run:
        ws.print_config()


def workspace_manage_software_setup_parser(subparser):
    """manage workspace software definitions"""

    subparser.add_argument(
        "--environment-name",
        "--env",
        dest="environment_name",
        metavar="ENV",
        help="Name of environment to define",
    )

    env_types = subparser.add_mutually_exclusive_group()
    env_types.add_argument(
        "--environment-packages",
        dest="environment_packages",
        help="Comma separated list of packages to add into environment",
        metavar="PKG1,PKG2,PKG2",
    )

    env_types.add_argument(
        "--external-env",
        dest="external_env_path",
        help="Path to external environment description",
        metavar="PATH",
    )

    subparser.add_argument(
        "--package-name",
        "--pkg",
        dest="package_name",
        metavar="NAME",
        help="Name of package to define",
    )

    subparser.add_argument(
        "--package-spec",
        "--pkg-spec",
        "--spec",
        dest="package_spec",
        metavar="SPEC",
        help="Value for the pkg_spec attribute in the defined package",
    )

    subparser.add_argument(
        "--compiler-package",
        "--compiler-pkg",
        "--compiler",
        dest="compiler_package",
        metavar="PKG",
        help="Value for the compiler attribute in the defined package",
    )

    subparser.add_argument(
        "--compiler-spec",
        dest="compiler_spec",
        metavar="SPEC",
        help="Value for the compiler_spec attribute in the defined package",
    )

    subparser.add_argument(
        "--package-manager-prefix",
        "--prefix",
        dest="package_manager_prefix",
        metavar="PREFIX",
        help="Prefix for defined package attributes. "
        "Resulting attributes will be {prefix}_pkg_spec.",
    )

    modify_types = subparser.add_mutually_exclusive_group()
    modify_types.add_argument(
        "--remove",
        "--delete",
        action="store_true",
        help="Whether to remove named package and environment definitions if they exist.",
    )

    modify_types.add_argument(
        "--overwrite",
        "-o",
        action="store_true",
        help="Whether to overwrite existing definitions or not.",
    )

    subparser.add_argument(
        "--dry-run",
        "--print",
        dest="dry_run",
        action="store_true",
        help="perform a dry run. Print resulting config to screen and not "
        + "to the workspace configuration file",
    )


def workspace_manage_software(args):
    """Execute workspace manage software command"""

    ws = ramble.cmd.find_workspace(args)

    if ws is None:
        import tempfile

        logger.warn("No active workspace found. Defaulting to `--dry-run`")

        root = tempfile.TemporaryDirectory()
        ws = ramble.workspace.Workspace(str(root))
        ws.dry_run = True
    else:
        ws.dry_run = args.dry_run

    if args.package_name:
        ws.manage_packages(
            args.package_name,
            args.package_spec,
            args.compiler_package,
            args.compiler_spec,
            args.package_manager_prefix,
            args.remove,
            args.overwrite,
        )

    if args.environment_name:
        ws.manage_environments(
            args.environment_name,
            args.environment_packages,
            args.external_env_path,
            args.remove,
            args.overwrite,
        )

    if ws.dry_run:
        ws.print_config()


def workspace_manage_includes_setup_parser(subparser):
    """manage workspace includes"""
    actions = subparser.add_mutually_exclusive_group()
    actions.add_argument(
        "--list", "-l", action="store_true", help="whether to print existing includes"
    )

    actions.add_argument(
        "--remove",
        "-r",
        dest="remove_pattern",
        metavar="PATTERN",
        help="whether to remove an existing include by name / pattern",
    )

    actions.add_argument(
        "--remove-index",
        dest="remove_index",
        metavar="IDX",
        help="whether to remove an existing include by index",
    )

    actions.add_argument(
        "--add", "-a", dest="add_include", metavar="PATH", help="whether to add a new include"
    )


def workspace_manage_includes(args):
    """Execute workspace manage include command"""

    ws = ramble.cmd.require_active_workspace(cmd_name="workspace manage includes")

    if args.list:
        with ws.read_transaction():
            workspace_dict = ws._get_workspace_dict()
            if namespace.include in workspace_dict[namespace.ramble]:
                includes = workspace_dict[namespace.ramble][namespace.include]
                if includes:
                    logger.msg("Workspace includes:")
                    for idx, include in enumerate(includes):
                        logger.msg(f"{idx}: {include}")
                    return
            logger.msg("Workspace contains no includes.")
    elif args.remove_index:
        remove_index = int(args.remove_index)
        with ws.write_transaction():
            ws.remove_include(index=remove_index)
    elif args.remove_pattern:
        with ws.write_transaction():
            ws.remove_include(pattern=args.remove_pattern)
    elif args.add_include:
        with ws.write_transaction():
            ws.add_include(args.add_include)


def workspace_generate_config_setup_parser(subparser):
    """generate current workspace config"""
    workspace_manage_experiments_setup_parser(subparser)


def workspace_generate_config(args):
    """Generate a configuration file for this ramble workspace"""
    workspace_manage_experiments(args)


def workspace_experiment_logs_setup_parser(subparser):
    """print log information for workspace"""
    default_filters = subparser.add_mutually_exclusive_group()
    default_filters.add_argument(
        "--limit-one", action="store_true", help="only print the first log information block"
    )

    default_filters.add_argument(
        "--first-failed",
        action="store_true",
        help="only print the information for the first failed experiment. "
        + "Requires `ramble workspace analyze` to have been run previously",
    )

    default_filters.add_argument(
        "--failed", action="store_true", help="print only failed experiment logs"
    )

    arguments.add_common_arguments(
        subparser,
        ["where", "exclude_where", "filter_tags"],
    )


def workspace_experiment_logs(args):
    """Print log information for workspace"""

    current_pipeline = ramble.pipeline.pipelines.logs
    ws = ramble.cmd.require_active_workspace(cmd_name="workspace concretize")

    first_only = args.limit_one or args.first_failed
    where_filter = args.where.copy() if args.where else []
    exclude_filter = args.exclude_where.copy() if args.exclude_where else []
    only_failed = args.first_failed or args.failed

    if only_failed:
        exclude_filter.append(["'{experiment_status}' == 'SUCCESS'"])

    filters = ramble.filters.Filters(
        include_where_filters=where_filter,
        exclude_where_filters=exclude_filter,
        tags=args.filter_tags,
    )

    pipeline_cls = ramble.pipeline.pipeline_class(current_pipeline)
    pipeline = pipeline_cls(ws, filters, first_only=first_only)
    with ws.write_transaction():
        workspace_run_pipeline(args, pipeline)


#: Dictionary mapping subcommand names and aliases to functions
subcommand_functions = {}


def sanitize_arg_name(base_name):
    """Allow function names to be remapped (eg `-` to `_`)"""
    formatted_name = base_name.replace("-", "_")
    return formatted_name


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest="workspace_command")

    for name in subcommands:
        if isinstance(name, (list, tuple)):
            name, aliases = name[0], name[1:]
        else:
            aliases = []

        # add commands to subcommands dict
        function_name = sanitize_arg_name("workspace_%s" % name)

        function = globals()[function_name]
        for alias in [name] + aliases:
            subcommand_functions[alias] = function

        # make a subparser and run the command's setup function on it
        setup_parser_cmd_name = sanitize_arg_name("workspace_%s_setup_parser" % name)
        setup_parser_cmd = globals()[setup_parser_cmd_name]

        subsubparser = sp.add_parser(
            name,
            aliases=aliases,
            help=setup_parser_cmd.__doc__,
            description=setup_parser_cmd.__doc__,
        )
        setup_parser_cmd(subsubparser)


def workspace(parser, args):
    """Look for a function called workspace_<name> and call it."""
    action = subcommand_functions[args.workspace_command]
    action(args)


manage_subcommand_functions = {}


def workspace_manage(args):
    """Look for a function for the manage subcommand, and execute it."""
    action = manage_subcommand_functions[args.manage_command]
    action(args)


def workspace_manage_setup_parser(subparser):
    """manage workspace definitions"""
    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest="manage_command")

    for name in manage_commands:
        if isinstance(name, (list, tuple)):
            name, aliases = name[0], name[1:]
        else:
            aliases = []

        # add commands to subcommands dict
        function_name = sanitize_arg_name("workspace_manage_%s" % name)

        function = globals()[function_name]
        for alias in [name] + aliases:
            manage_subcommand_functions[alias] = function

        # make a subparser and run the command's setup function on it
        setup_parser_cmd_name = sanitize_arg_name("workspace_manage_%s_setup_parser" % name)
        setup_parser_cmd = globals()[setup_parser_cmd_name]

        subsubparser = sp.add_parser(
            name,
            aliases=aliases,
            help=setup_parser_cmd.__doc__,
            description=setup_parser_cmd.__doc__,
        )
        setup_parser_cmd(subsubparser)
