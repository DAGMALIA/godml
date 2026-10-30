# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.serve.model_loader``."""

from godml.core.deprecation import alias_module

alias_module("godml.model_service.model_loader", "godml.serve.model_loader")
