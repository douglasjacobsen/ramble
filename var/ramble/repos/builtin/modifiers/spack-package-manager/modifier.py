# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403
from ramble.software_environments import ExternalEnvironment


class SpackPackageManager(BasicModifier):
    """Prototype Modifier for package manager abstractions"""

    name = 'spack-package-manager'

    mode('spack', description='Default mode for spack package manager')
    default_mode('spack')

    register_phase('software_install_requested_compilers', pipeline='setup',
                   run_after=['software_create_env'])

    def __init__(self, file_path):
        super().__init__(file_path)

        self.keywords = ramble.keywords.keywords
        self.spack_runner = ramble.spack_runner.SpackRunner()

    def _software_install_requested_compilers(self, workspace, app_inst=None):
        """Install compilers an application uses"""
        # See if we cached this already, and if so return
        env_path = self.expander.env_path
        if not env_path:
            raise ApplicationError('Ramble env_path is set to None.')
        logger.msg('Installing compilers')

        cache_tupl = ('spack-compilers', env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug('{} already in cache.'.format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            self.spack_runner.set_compiler_config_dir(workspace.auxiliary_software_dir)
            self.spack_runner.set_dry_run(workspace.dry_run)

            app_context = self.expander.expand_var_name(self.keywords.env_name)

            software_envs = workspace.software_environments
            software_env = software_envs.render_environment(app_context, self.expander)

            for compiler_spec in software_envs.compiler_specs_for_environment(software_env):
                logger.debug(f'Installing compiler: {compiler_spec}')
                self.spack_runner.install_compiler(compiler_spec)

        except ramble.spack_runner.RunnerError as e:
            logger.die(e)

    register_phase('software_create_env', pipeline='mirror')
    register_phase('software_create_env', pipeline='setup')
    register_phase('software_create_env', pipeline='pushdeployment')

    def _software_create_env(self, workspace, app_inst=None):
        """Create the spack environment for this experiment

        Extract all specs this experiment uses, and write the spack environment
        file for it.
        """

        logger.msg('Creating Spack environment')

        # See if we cached this already, and if so return
        env_path = self.expander.env_path
        if not env_path:
            raise ApplicationError('Ramble env_path is set to None.')

        cache_tupl = ('spack-env', env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug('{} already in cache.'.format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        package_manager_config_dicts = [self.package_manager_configs]
        for mod_inst in app_inst._modifier_instances:
            package_manager_config_dicts.append(mod_inst.package_manager_configs)

        for config_dict in package_manager_config_dicts:
            for _, config in config_dict.items():
                self.spack_runner.add_config(config)

        try:
            self.spack_runner.set_dry_run(workspace.dry_run)
            self.spack_runner.create_env(self.expander.expand_var_name(self.keywords.env_path))
            self.spack_runner.activate()

            # Write auxiliary software files into created spack env.
            for name, contents in workspace.all_auxiliary_software_files():
                aux_file_path = self.expander.expand_var(
                    os.path.join(
                        self.expander.expansion_str(self.keywords.env_path),
                        f'{name}'
                    )
                )
                self.spack_runner.add_include_file(aux_file_path)
                with open(aux_file_path, 'w+') as f:
                    f.write(self.expander.expand_var(contents))

            env_context = self.expander.expand_var_name(self.keywords.env_name)
            software_envs = workspace.software_environments
            software_env = software_envs.render_environment(env_context, self.expander)
            if isinstance(software_env, ExternalEnvironment):
                self.spack_runner.copy_from_external_env(software_env.external_env)
            else:
                for pkg_spec in software_envs.package_specs_for_environment(software_env):
                    self.spack_runner.add_spec(pkg_spec)

                self.spack_runner.generate_env_file()

            added_packages = set(self.spack_runner.added_packages())
            logger.debug(f' All added packages: {added_packages}')
            for pkg in app_inst.required_packages.keys():
                if pkg not in added_packages:
                    logger.die(f'Software spec {pkg} is not defined '
                               f'in environment {env_context}, but is '
                               f'required by the {self.name} application '
                               'definition')

            for mod_inst in app_inst._modifier_instances:
                for pkg in mod_inst.required_packages.keys():
                    if pkg not in added_packages:
                        logger.die(f'Software spec {pkg} is not defined '
                                   f'in environment {env_context}, but is '
                                   f'required by the {mod_inst.name} modifier '
                                   'definition')

            self.spack_runner.deactivate()

        except ramble.spack_runner.RunnerError as e:
            logger.die(e)

    register_phase('software_configure', pipeline='setup',
                   run_after=['software_create_env', 'software_install_requested_compilers'])

    def _software_configure(self, workspace, app_inst=None):
        """Concretize the spack environment for this experiment

        Perform spack's concretize step on the software environment generated
        for  this experiment.
        """

        logger.msg('Concretizing Spack environment')

        # See if we cached this already, and if so return
        env_path = self.expander.env_path

        cache_tupl = ('concretize-env', env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug('{} already in cache.'.format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            self.spack_runner.set_dry_run(workspace.dry_run)

            self.spack_runner.activate()

            env_concretized = self.spack_runner.concretized

            if not env_concretized:
                self.spack_runner.concretize()

        except ramble.spack_runner.RunnerError as e:
            logger.die(e)

    register_phase('software_install', pipeline='setup',
                   run_after=['software_configure'])

    def _software_install(self, workspace, app_inst=None):
        """Install application's software using spack"""

        # See if we cached this already, and if so return
        env_path = self.expander.env_path

        cache_tupl = ('spack-install', env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug('{} already in cache.'.format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            self.spack_runner.set_dry_run(workspace.dry_run)
            self.spack_runner.set_env(env_path)

            logger.msg('Installing software')

            self.spack_runner.activate()
            self.spack_runner.install()
        except ramble.spack_runner.RunnerError as e:
            logger.die(e)

    register_phase('evaluate_requirements', pipeline='setup',
                   run_after=['software_install'])

    def _evaluate_requirements(self, workspace, app_inst=None):
        """Evaluate all requirements for this experiment"""

        for mod_inst in app_inst._modifier_instances:
            for req in mod_inst.all_package_manager_requirements():
                expanded_req = {}
                for key, val in req.items():
                    expanded_req[key] = self.expander.expand_var(val)
                self.spack_runner.validate_command(**expanded_req)

    register_phase('define_package_paths', pipeline='setup',
                   run_after=['software_install', 'evaluate_requirements'],
                   run_before=['make_experiments'])

    def _define_package_paths(self, workspace, app_inst=None):
        """Define variables containing the path to all spack packages

        For every spack package defined within an application context, define
        a variable that refers to that packages installation location.

        As an example:
        <ramble.yaml>
        spack:
          applications:
            wrfv4:
              wrf:
                base: wrf
                version: 4.2.2

        Would define a variable `wrf` that contains the installation path of
        wrf@4.2.2
        """

        logger.msg('Defining Spack variables')

        try:
            self.spack_runner.set_dry_run(workspace.dry_run)
            self.spack_runner.set_env(self.expander.env_path)

            self.spack_runner.activate()

            app_context = self.expander.expand_var_name(self.keywords.env_name)

            software_environments = workspace.software_environments
            software_environment = software_environments.render_environment(app_context,
                                                                            self.expander)

            for pkg_spec in \
                    software_environments.package_specs_for_environment(software_environment):
                spack_pkg_name, package_path = self.spack_runner.get_package_path(pkg_spec)
                app_inst.variables[spack_pkg_name] = package_path

        except ramble.spack_runner.RunnerError as e:
            logger.die(e)

    register_phase('mirror_software', pipeline='mirror', run_after=['software_create_env'])

    def _mirror_software(self, workspace, app_inst=None):
        """Mirror software source for this experiment using spack"""
        import re

        logger.msg('Mirroring software')

        # See if we cached this already, and if so return
        env_path = self.expander.env_path
        if not env_path:
            raise ApplicationError('Ramble env_path is set to None.')

        cache_tupl = ('spack-mirror', env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug('{} already in cache.'.format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            self.spack_runner.set_dry_run(workspace.dry_run)
            self.spack_runner.set_env(env_path)

            self.spack_runner.activate()

            mirror_output = self.spack_runner.mirror_environment(workspace.software_mirror_path)

            present = 0
            added = 0
            failed = 0

            present_regex = re.compile(r'\s+(?P<num>[0-9]+)\s+already present')
            present_match = present_regex.search(mirror_output)
            if present_match:
                present = int(present_match.group('num'))

            added_regex = re.compile(r'\s+(?P<num>[0-9]+)\s+added')
            added_match = added_regex.search(mirror_output)
            if added_match:
                added = int(added_match.group('num'))

            failed_regex = re.compile(r'\s+(?P<num>[0-9]+)\s+failed to fetch.')
            failed_match = failed_regex.search(mirror_output)
            if failed_match:
                failed = int(failed_match.group('num'))

            added_start = len(workspace.software_mirror_stats.new)
            for i in range(added_start, added_start + added):
                workspace.software_mirror_stats.new[i] = i

            present_start = len(workspace.software_mirror_stats.present)
            for i in range(present_start, present_start + present):
                workspace.software_mirror_stats.present[i] = i

            error_start = len(workspace.software_mirror_stats.errors)
            for i in range(error_start, error_start + failed):
                workspace.software_mirror_stats.errors.add(i)

        except ramble.spack_runner.RunnerError as e:
            logger.die(e)

    register_phase('push_to_spack_cache', pipeline='pushtocache', run_after=[])

    def _push_to_spack_cache(self, workspace, app_inst=None):

        env_path = self.expander.env_path
        cache_tupl = ('push-to-cache', env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug('{} already pushed, skipping'.format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            self.spack_runner.set_dry_run(workspace.dry_run)
            self.spack_runner.set_env(env_path)
            self.spack_runner.activate()

            self.spack_runner.push_to_spack_cache(workspace.spack_cache_path)

            self.spack_runner.deactivate()
        except ramble.spack_runner.RunnerError as e:
            logger.die(e)

    def populate_inventory(self, workspace, force_compute=False, require_exist=False):
        """Add software environment information to hash inventory"""

        env_path = self.expander.env_path
        self.spack_runner.set_dry_run(workspace.dry_run)
        self.spack_runner.set_env(env_path, require_exists=False)
        self.spack_runner.activate()
        self.hash_inventory['software'].append(
            {
                'name': self.spack_runner.env_path.replace(workspace.root + os.path.sep, ''),
                'digest': self.spack_runner.inventory_hash()
            }
        )
        self.spack_runner.deactivate()

        super().populate_inventory(workspace, force_compute, require_exist)

    def _clean_hash_variables(self, workspace, variables):
        """Perform spack specific cleanup of variables before hashing"""

        self.spack_runner.configure_env(self.expander.expand_var_name(self.keywords.env_path))
        self.spack_runner.activate()

        for var in variables:
            if isinstance(variables[var], six.string_types):
                variables[var] = variables[var].replace(
                    '\n'.join(self.spack_runner.generate_source_command()),
                    'spack_source'
                )
                variables[var] = variables[var].replace(
                    '\n'.join(self.spack_runner.generate_activate_command()),
                    'spack_activate'
                )

        self.spack_runner.deactivate()

        super()._clean_hash_variables(workspace, variables)

    register_phase('deploy_artifacts', pipeline='pushdeployment',
                   run_after=['software_create_env'])

    def _deploy_artifacts(self, workspace, app_inst=None):
        super()._deploy_artifacts(workspace, app_inst=app_inst)
        env_path = self.expander.env_path

        try:
            self.spack_runner.set_dry_run(workspace.dry_run)
            self.spack_runner.set_env(env_path)
            self.spack_runner.activate()

            repo_path = os.path.join(workspace.named_deployment, 'object_repo')

            for pkg, pkg_def in self.spack_runner.package_definitions():
                pkg_dir_name = os.path.basename(os.path.dirname(pkg_def))
                pkg_dir = os.path.join(repo_path, 'packages', pkg_dir_name)
                fs.mkdirp(pkg_dir)
                shutil.copyfile(pkg_def, os.path.join(pkg_dir, 'package.py'))

            self.spack_runner.deactivate()

        except ramble.spack_runner.RunnerError as e:
            logger.die(e)

    register_builtin('spack_source', required=True, depends_on=['builtin::env_vars'])
    register_builtin('spack_activate', required=True, depends_on=['modifier_builtin::spack-package-manager::spack_source'])
    register_builtin('spack_deactivate', required=False, depends_on=['modifier_builtin::spack-package-manager::spack_source'])

    def spack_source(self):
        return self.spack_runner.generate_source_command()

    def spack_activate(self):
        self.spack_runner.configure_env(self.expander.expand_var_name(self.keywords.env_path))
        self.spack_runner.activate()
        cmds = self.spack_runner.generate_activate_command()
        self.spack_runner.deactivate()
        return cmds

    def spack_deactivate(self):
        return self.spack_runner.generate_deactivate_command()
