# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.govern.compliance.validation_helpers``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.compliance_service.validation_helpers",
    "godml.govern.compliance.validation_helpers",
)
