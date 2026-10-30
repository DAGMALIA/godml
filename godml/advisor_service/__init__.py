# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecated 1.x import path: use ``godml.tools.advisor``."""

from godml.core.deprecation import reexport_package

reexport_package(globals(), "godml.advisor_service", "godml.tools.advisor")
