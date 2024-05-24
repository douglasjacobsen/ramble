# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for spack.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/spack.py
   :lines: 12-
"""  # noqa E501


#: Properties for inclusion in other schemas
properties = {
    'spack': {
        'type': 'object',
        'properties': {
            'packages': {
                'type': 'object',
                'additionalProperties': {
                    'type': 'object',
                    'properties': {
                        'spack_spec': {'type': 'string'},
                        'compiler_spec': {
                            'type': 'string',
                            'default': None,
                        },
                        'compiler': {
                            'type': 'string',
                            'default': None,
                        },
                    },
                    'additionalProperties': False,
                    'default': {}
                },
            },
            'environments': {
                'type': 'object',
                'properties': {},
                'default': {},
                'additionalProperties': {
                    'type': 'object',
                    'properties': {
                        'external_spack_env': {
                            'type': 'string',
                            'default': None,
                        },
                        'packages': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'default': []
                        },
                    },
                    'additionalProperties': False,
                    'default': {}
                }
            }
        },
        'default': {},
        'additionalProperties': False,
    }
}


#: Full schema with metadata
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'Spack software configuration file schema',
    'type': 'object',
    'additionalProperties': False,
    'properties': properties,
}


def update(data):

    changed = False

    """
    This entire section is deprecated.
    Replicate this into a `software` section instead.
    """

    old_data = data.copy()

    pkg_keymap = {
        'spack_spec': 'pkg_spec',
        'compiler': 'compiler',
        'compiler_spec': 'compiler_spec',
    }

    if 'packages' in old_data:
        for pkg_name, pkg_def in old_data['packages'].items():
            for key, newkey in pkg_keymap.items():
                if key in pkg_def:
                    if key in data['packages'][pkg_name]:
                        del data['packages'][pkg_name][key]
                    changed = True
                    data['packages'][pkg_name][newkey] = pkg_def[key]

    return changed
