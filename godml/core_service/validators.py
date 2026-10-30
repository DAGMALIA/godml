# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.govern.validators``."""

from godml.core.deprecation import alias_module

alias_module("godml.core_service.validators", "godml.govern.validators")
