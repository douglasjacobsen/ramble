# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import collections.abc
from typing import Optional, Any, Union, Callable
import ramble.error

reserved_variants = {"package_manager", "package_manager_prefix", "workflow_manager", "version"}


def validate_variant(variant: str):
    """Check if a variant name is valid or not

    If the input variant name is not valid, this function will raise an
    exception. Otherwise this function will not perform any actions.

    Args:
        variant (str): Variant name to test
    """

    if variant in reserved_variants:
        raise RambleVariantError(
            f"Variant {variant} is invalid, as this name is reserved by ramble"
        )


def define_variant(
    obj,
    name: str,
    default: Optional[Any] = None,
    description: str = "",
    values: Optional[Union[collections.abc.Sequence, Callable[[Any], bool]]] = None,
):
    """Define a new variant in the input object

    Args:
        obj: Input ramble object to define variant inside.
        name (str): Name of variant to define
        default: Default value of the new variant
        description (str): Description of the variant
        values: Values for variant.
    """

    if values is not None and default is not None:
        if default not in values:
            raise RambleVariantError(
                f"Variant {name} defined with a default of {default} which "
                f"is not in defined values of {values}"
            )

    if isinstance(default, str):
        obj.object_variants.add(f"{name}={default}")
    elif isinstance(default, bool):
        if default:
            obj.object_variants.add(f"+{name}")
        else:
            obj.object_variants.add(f"~{name}")


class RambleVariantError(ramble.error.RambleError):
    """Class representing errors with variants"""
