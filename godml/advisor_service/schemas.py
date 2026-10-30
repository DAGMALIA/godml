# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.tools.advisor.schemas``."""

from godml.core.deprecation import alias_module

alias_module("godml.advisor_service.schemas", "godml.tools.advisor.schemas")
