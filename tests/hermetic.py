# hermetic.py
"""Snapshot helpers for the hermetic-tests guard (F1-19, CLAUDE.md)."""

import os
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def _skipped_file(name: str) -> bool:
    # pytest-cov writes its data and reports in the rootdir
    return name.startswith(".coverage") or name == "coverage.xml"


def snapshot(root: Path) -> dict[str, int]:
    """Relative path -> mtime (ns) of every file under root, minus caches."""
    files: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info")
        ]
        for name in filenames:
            if _skipped_file(name):
                continue
            path = Path(dirpath, name)
            try:
                files[path.relative_to(root).as_posix()] = path.stat().st_mtime_ns
            except OSError:  # removed while walking
                continue
    return files


def changed_files(root: Path, before: dict[str, int]) -> list[str]:
    """Files created or modified under root since `before`, sorted."""
    after = snapshot(root)
    return sorted(p for p, mtime in after.items() if before.get(p) != mtime)
