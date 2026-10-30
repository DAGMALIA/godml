# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.govern.compliance.compliance_registry``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.compliance_service.compliance_registry",
    "godml.govern.compliance.compliance_registry",
)
