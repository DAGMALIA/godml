# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.tools.notebook_api.pipeline``."""

from godml.core.deprecation import alias_module

alias_module("godml.notebook_api.pipeline", "godml.tools.notebook_api.pipeline")
