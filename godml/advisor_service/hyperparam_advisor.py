# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.tools.advisor.hyperparam_advisor``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.advisor_service.hyperparam_advisor", "godml.tools.advisor.hyperparam_advisor"
)
