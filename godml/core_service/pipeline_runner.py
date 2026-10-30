# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.govern.pipeline_runner``."""

from godml.core.deprecation import alias_module

alias_module("godml.core_service.pipeline_runner", "godml.govern.pipeline_runner")
