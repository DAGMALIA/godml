# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Deprecation of the GoDML 1.x import paths (F2-01).

GoDML 2.0 groups modules by pillar (core, govern, train, serve, observe,
tools). Every 1.x module path still imports, through a shim that emits
`GoDMLDeprecationWarning` and hands back the module at its new path, so
`isinstance` checks and `mock.patch` on old paths keep working.
"""

from __future__ import annotations

import importlib
import sys
import warnings
from typing import Any


class GoDMLDeprecationWarning(DeprecationWarning):
    """A GoDML API (such as a 1.x import path) is deprecated."""


# Frames from `warnings.warn` up to the importer: `_warn`, the public helper,
# the shim's module body, then the importing code (importlib frames are
# skipped by `warnings` itself).
_STACKLEVEL = 4


def _warn(message: str) -> None:
    warnings.warn(message, GoDMLDeprecationWarning, stacklevel=_STACKLEVEL)


def alias_module(old: str, new: str) -> None:
    """Make the 1.x module `old` resolve to the module object at `new`."""
    _warn(f"'{old}' is deprecated since GoDML 2.0; import '{new}' instead.")
    sys.modules[old] = importlib.import_module(new)


def reexport_package(namespace: dict[str, Any], old: str, new: str) -> None:
    """Expose the public names of package `new` from the 1.x package `old`.

    The old package stays a real package (not an alias): aliasing it would
    make Python load each submodule a second time under the old name.
    """
    _warn(f"'{old}' is deprecated since GoDML 2.0; import '{new}' instead.")
    package = importlib.import_module(new)
    names = getattr(package, "__all__", None) or [
        n for n in vars(package) if not n.startswith("_")
    ]
    namespace.update({n: getattr(package, n) for n in names})


def warn_split_package(old: str) -> None:
    """Warn on import of a 1.x package whose modules moved to several pillars."""
    _warn(
        f"'{old}' is deprecated since GoDML 2.0: its modules moved to the "
        "pillars (godml.core, godml.govern, godml.train, godml.serve, "
        "godml.observe, godml.tools); import them from their new paths."
    )
