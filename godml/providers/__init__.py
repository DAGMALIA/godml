# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.train.providers``."""

from godml.core.deprecation import reexport_package

reexport_package(globals(), "godml.providers", "godml.train.providers")
