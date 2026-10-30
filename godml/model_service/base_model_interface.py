# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.train.models.base_model_interface``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.model_service.base_model_interface",
    "godml.train.models.base_model_interface",
)
