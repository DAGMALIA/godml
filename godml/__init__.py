# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
# Importing godml has no side effects (F1-12): no env vars, warning filters
# or logging setup. The CLI configures its own output (godml_cli.main).
from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("godml")
except PackageNotFoundError:  # source tree without an install
    __version__ = "0.0.0+unknown"

__all__ = [
    "GodmlNotebook",
    "quick_train",
    "train_from_yaml",
    "quick_train_yaml",
    "load_pipeline",
    "get_executor",
    "save_model_to_structure",
    "load_model_from_structure",
    "list_models",
    "promote_model",
]


# 🚀 Lazy import: solo se cargan los módulos pesados si alguien realmente los usa
def __getattr__(name):
    if name in {"GodmlNotebook", "quick_train", "train_from_yaml", "quick_train_yaml"}:
        from . import notebook_api

        return getattr(notebook_api, name)

    if name in {"load_pipeline"}:
        from .core_service import parser

        return parser.load_pipeline

    if name in {"get_executor"}:
        from .core_service import executors

        return executors.get_executor

    if name in {
        "save_model_to_structure",
        "load_model_from_structure",
        "list_models",
        "promote_model",
    }:
        from .utils import model_storage

        return getattr(model_storage, name)

    raise AttributeError(f"module {__name__} has no attribute {name}")


# print("✅ godml/__init__.py cargado y logs silenciados")
