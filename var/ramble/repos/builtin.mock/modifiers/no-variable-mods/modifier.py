# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class NoVariableMods(BasicModifier):
    """Define modifier with no variable modifications"""

    name = "no-variable-mods"

    tags("test")

    mode("test", description="This is a test mode")
