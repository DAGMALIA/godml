# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.govern.compliance.compliance_utils``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.compliance_service.compliance_utils",
    "godml.govern.compliance.compliance_utils",
)
