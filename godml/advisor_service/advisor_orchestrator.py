# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.tools.advisor.advisor_orchestrator``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.advisor_service.advisor_orchestrator",
    "godml.tools.advisor.advisor_orchestrator",
)
