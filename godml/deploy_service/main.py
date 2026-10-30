# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.serve.deploy.main``."""

from godml.core.deprecation import alias_module

alias_module("godml.deploy_service.main", "godml.serve.deploy.main")
