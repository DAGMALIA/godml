# test_version.py
"""
The package version has a single source: the installed metadata (pyproject).
Hardcoded copies drifted before (server.py reported 1.1.0, banners v1.0.2).
"""

import importlib.metadata
from pathlib import Path

import godml
from godml.tools.yaml_utils import generate_readme_md

PACKAGE_DIR = Path(godml.__file__).parent


def test_version_comes_from_metadata():
    assert godml.__version__ == importlib.metadata.version("godml")


# Files that cite a fixed past release (not the current version), e.g. the
# fail-closed error pointing users to "CHANGELOG 1.4.0".
HISTORICAL_VERSION_REFERENCES = {"compliance_service/errors.py"}


def find_hardcoded_version(version: str) -> list[str]:
    return [
        path.relative_to(PACKAGE_DIR).as_posix()
        for path in PACKAGE_DIR.rglob("*")
        if path.suffix in {".py", ".txt", ".yml", ".yaml", ".toml"}
        and path.relative_to(PACKAGE_DIR).as_posix()
        not in HISTORICAL_VERSION_REFERENCES
        and version in path.read_text(encoding="utf-8", errors="ignore")
    ]


def test_no_hardcoded_package_version_in_sources():
    assert find_hardcoded_version(importlib.metadata.version("godml")) == []


def test_generated_readme_uses_installed_version():
    readme = generate_readme_md("demo")
    assert f"v{godml.__version__}" in readme
