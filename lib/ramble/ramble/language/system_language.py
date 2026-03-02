# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.language.shared_language


class SystemMeta(ramble.language.shared_language.SharedMeta):
    _directive_names = set()
    _directives_to_be_executed = []


system_directive = SystemMeta.directive


@system_directive("platforms")
def platform(name, **kwargs):
    """Adds a platform to this system

    Defines a new platform that can be used within the context of
    its system.

    Args:
        name (str): The name of a platform to be used
    """

    def _execute_platform(env):
        if not hasattr(env, "platforms"):
            env.platforms = ramble.util.directives.DirectiveDict()
            env.platforms.directive_name = "platforms"

        env.platforms[name] = kwargs

    return _execute_platform


@system_directive("description")
def description(text, **kwargs):
    """Adds a description to this system

    Args:
        text (str): The description of the system
    """

    def _execute_description(env):
        env.description = text

    return _execute_description
