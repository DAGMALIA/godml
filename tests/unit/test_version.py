# test_version.py
"""
The package version has a single source: the installed metadata (pyproject).
Hardcoded copies drifted before (server.py reported 1.1.0, banners v1.0.2).
"""

import importlib.metadata
from pathlib import Path

import godml
from godml.utils.yaml_utils import generate_readme_md

PACKAGE_DIR = Path(godml.__file__).parent


def test_version_comes_from_metadata():
    assert godml.__version__ == importlib.metadata.version("godml")


def test_no_hardcoded_package_version_in_sources():
    version = importlib.metadata.version("godml")
    offenders = [
        str(path.relative_to(PACKAGE_DIR))
        for path in PACKAGE_DIR.rglob("*")
        if path.suffix in {".py", ".txt", ".yml", ".yaml", ".toml"}
        and version in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == []


def test_generated_readme_uses_installed_version():
    readme = generate_readme_md("demo")
    assert f"v{godml.__version__}" in readme
