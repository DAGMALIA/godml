# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.train.log_model_generic``."""

from godml.core.deprecation import alias_module

alias_module("godml.utils.log_model_generic", "godml.train.log_model_generic")
