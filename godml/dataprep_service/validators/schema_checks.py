# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.train.dataprep.validators.schema_checks``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.dataprep_service.validators.schema_checks",
    "godml.train.dataprep.validators.schema_checks",
)
