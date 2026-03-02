# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.repository
from ramble.language.shared_language import SharedMeta
import ramble.variants

ObjectMixin = ramble.repository.get_base_class("object-mixin")


class PlatformBase(ObjectMixin, metaclass=SharedMeta):
    _language_classes = [SharedMeta]
    platform_class = "PlatformBase"

    def __init__(self, file_path):
        super().__init__()
        self.object_variants = ramble.variants.VariantSet()

        for var_args in self.class_variants.values():
            self.object_variants.add_variant(**var_args)

        self._file_path = file_path
