# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.repository
from ramble.language.system_language import platform, description

SystemBase = ramble.repository.get_base_class("system-base")

class UserDefined(SystemBase):
    """A user defined system."""

    name = "user-defined"

    description("A default system to represent a user defined cluster.")
    platform("user-defined")
