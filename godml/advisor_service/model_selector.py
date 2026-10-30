# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.tools.advisor.model_selector``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.advisor_service.model_selector", "godml.tools.advisor.model_selector"
)
