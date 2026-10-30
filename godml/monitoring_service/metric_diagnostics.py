# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.train.metric_diagnostics``."""

from godml.core.deprecation import alias_module

alias_module(
    "godml.monitoring_service.metric_diagnostics", "godml.train.metric_diagnostics"
)
