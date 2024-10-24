# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.language.language_base
from ramble.language.language_base import DirectiveError


class ApplicationMeta(ramble.language.language_base.DirectiveMeta):
    _directive_names = set()
    _diretives_to_be_executed = []


application_directive = ApplicationMeta.directive


@application_directive('workloads')
def workload(name, executables=None, executable=None, input=None,
             inputs=None, **kwargs):
    """Adds a workload to this application

    Defines a new workload that can be used within the context of
    its application.

    Input arguments:
        - executable: The name of an executable to be used
        - executables: A list of executable names to be used
        - input (Optional): The name of an input be used
        - inputs (Optional): A list of input names that will be used

    Either executable, or executables is a required input argument.
    """

    def _execute_workload(app):
        app.workloads[name] = {
            'executables': [],
            'inputs': []
        }

        found_exec = False
        if executables:
            found_exec = True
            if isinstance(executables, list):
                app.workloads[name]['executables'].extend(
                    executables)
            else:
                app.workloads[name]['executables'].append(
                    executables.copy())

        if executable:
            found_exec = True
            app.workloads[name]['executables'].append(executable)

        if not found_exec:
            raise DirectiveError('workload directive requires one of:\n' +
                                 '  executable\n' +
                                 '  executables\n')

        if inputs:
            if isinstance(inputs, list):
                app.workloads[name]['inputs'].extend(inputs)
            else:
                app.workloads[name]['inputs'].append(inputs)

        if input:
            app.workloads[name]['inputs'].append(input)

    return _execute_workload


@application_directive('executables')
def executable(name, template, use_mpi=False, redirect='{log_file}', **kwargs):
    """Adds an executable to this application

    Defines a new executable that can be used to configure workloads and
    experiments with.

    Executables may or may not use MPI.

    Arguments:
     - template: The template command this executable should generate from
     - use_mpi: (Boolean) determines if this executable should be
                 wrapped with an `mpirun` like command or not.
     - redirect (optional): Sets the path for outputs to be written to.
                            defaults to {log_file}

    """

    def _execute_executable(app):
        app.executables[name] = \
            {
                'template': template,
                'mpi': use_mpi,
                'redirect': redirect
            }  # noqa: E123

    return _execute_executable


@application_directive('figure_of_merit_contexts')
def figure_of_merit_context(name, regex, output_format):
    """Defines a context for figures of merit

    Defines a new context to contain figures of merit.

    Inputs:
     - name: High level name of the context. Can be referred to in
             the figure of merit
     - regex: Regular expression, using group names, to match a context.
     - output_format: String, using python keywords {group_name} to
                      extract group names from context regular
                      expression.
    """

    def _execute_figure_of_merit_context(app):
        app.figure_of_merit_contexts[name] = {
            'regex': regex,
            'output_format': output_format
        }

    return _execute_figure_of_merit_context


@application_directive('archive_patterns')
def archive_pattern(pattern):
    """Adds a file pattern to be archived in addition to figure of merit logs

    Defines a new file pattern that will be archived during workspace archival.
    Archival will only happen for files that match the pattern when archival
    is being performed.

    Inputs:
      - pattern: Pattern that refers to files to archive
    """

    def _execute_archive_pattern(app):
        app.archive_patterns[pattern] = pattern

    return _execute_archive_pattern


@application_directive('figures_of_merit')
def figure_of_merit(name, log_file, fom_regex, group_name, units='',
                    contexts=[]):
    """Adds a figure of merit to track for this application

    Defines a new figure of merit.
    Inputs:
     - name: High level name of the figure of merit
     - log_file: File the figure of merit can be extracted from
     - fom_regex: A regular expression using named groups to extract the FOM
     - group_name: The name of the group that the FOM should be pulled from
     - units: The units associated with the FOM
     - keep_policy: The policy for determining which FOM(s) to keep
                    can be 'last' or 'all'
    """

    def _execute_figure_of_merit(app):
        app.figures_of_merit[name] = {
            'log_file': log_file,
            'regex': fom_regex,
            'group_name': group_name,
            'units': units,
            'contexts': contexts
        }

    return _execute_figure_of_merit


@application_directive('inputs')
def input_file(name, url, description, target_dir='{workload_name}', **kwargs):
    """Adds an input file defintion to this appliaction

    Defines a new input file.
    An input file must define it's name, and a url where the input can be
    fetched from.

    Arguments are:
      - url: Path to the input file / archive
      - description: Description of this input file
      - target_dir (Optional): The directory where the archive will be
                               expanded. Defaults to 'input'
    """

    def _execute_input_file(app):
        app.inputs[name] = {
            'url': url,
            'description': description,
            'target_dir': target_dir
        }

    return _execute_input_file


@application_directive('workload_variables')
def workload_variable(name, default, description, workload=None,
                      workloads=None, **kwargs):
    """Define a new variable to be used in experiments

    Defines a new variable that can be defined within the
    experiments.yaml config file, to control various aspects of
    an experiment.

    These are specific to each workload.
    """

    def _execute_workload_variable(app):
        if not (workload or workloads):
            raise DirectiveError('workload_variable directive requires:\n' +
                                 '  workload or workloads to be defined.')

        all_workloads = []
        if workload:
            all_workloads.append(workload)
        if workloads:
            if isinstance(workloads, list):
                all_workloads.extend(workloads)
            else:
                all_workloads.extend(workloads)

        for wl_name in all_workloads:
            if wl_name not in app.workload_variables:
                app.workload_variables[wl_name] = {}

            app.workload_variables[wl_name][name] = {
                'default': default,
                'description': description
            }

    return _execute_workload_variable


@application_directive('default_compilers')
def default_compiler(name, base, version=None, variants=None,
                     dependencies=None, arch=None, target=None,
                     custom_specifier=None):
    """Defines the default compiler that will be used with this application

    Adds a new compiler spec to this application. Software specs should
    reference a compiler that has been added.
    """

    def _execute_default_compiler(app):
        if app.uses_spack:
            app.default_compilers[name] = {
                'base': base,
                'version': version,
                'variants': variants,
                'dependencies': dependencies,
                'target': target,
                'arch': arch,
                'spec_type': 'compiler',
                'application_name': app.name,
                'custom_specifier': custom_specifier
            }

    return _execute_default_compiler


@application_directive('mpi_libraries')
def mpi_library(name, base, version=None, variants=None,
                dependencies=None, arch=None,
                target=None, custom_specifier=None):
    """Defines a new mpi library that software_specs can use

    Adds a new mpi_library to this app that can be referenced by
    software_specs.
    """

    def _execute_mpi_library(app):
        if app.uses_spack:
            app.mpi_libraries[name] = {
                'base': base,
                'version': version,
                'variants': variants,
                'dependencies': dependencies,
                'target': target,
                'arch': arch,
                'spec_type': 'mpi_library',
                'application_name': app.name,
                'custom_specifier': custom_specifier
            }

    return _execute_mpi_library


@application_directive('software_specs')
def software_spec(name, base, version=None, variants=None,
                  compiler=None, mpi=None, dependencies=None,
                  arch=None, target=None, custom_specifier=None,
                  required=False):
    """Defines a new software spec needed for this application.

    Adds a new software spec (for spack to use) that this application
    needs to execute properly.

    Only adds specs to applications that use spack.

    Specs can be described as an mpi spec, which means they
    will depend on the MPI library within the resulting spack
    environment.
    """

    def _execute_software_spec(app):
        if app.uses_spack:

            # Define the spec
            app.software_specs[name] = {
                'base': base,
                'version': version,
                'variants': variants,
                'compiler': compiler,
                'mpi': mpi,
                'dependencies': dependencies,
                'target': target,
                'arch': arch,
                'spec_type': 'package',
                'application_name': app.name,
                'custom_specifier': custom_specifier,
                'required': required
            }

    return _execute_software_spec
