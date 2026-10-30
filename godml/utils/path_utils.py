# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.core.path_utils``."""

from godml.core.deprecation import alias_module

alias_module("godml.utils.path_utils", "godml.core.path_utils")
