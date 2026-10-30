# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.observe.lineage.openlineage_emitter``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.dataprep_service.lineage.openlineage_emitter",
    "godml.observe.lineage.openlineage_emitter",
)
