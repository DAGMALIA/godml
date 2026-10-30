# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.train.dataprep.transforms.cast_types``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.dataprep_service.transforms.cast_types",
    "godml.train.dataprep.transforms.cast_types",
)
