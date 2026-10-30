# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.tools.advisor.metric_judge``."""

from godml.core.deprecation import alias_module

alias_module("godml.advisor_service.metric_judge", "godml.tools.advisor.metric_judge")
