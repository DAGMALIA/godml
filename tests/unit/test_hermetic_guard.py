# test_hermetic_guard.py
"""F1-19: the session guard reports files tests create or modify outside tmp_path."""

import os

from tests.hermetic import changed_files, snapshot


def test_reports_created_and_modified_files(tmp_path):
    existing = tmp_path / "logs" / "godml.log"
    existing.parent.mkdir()
    existing.write_text("old")
    before = snapshot(tmp_path)

    (tmp_path / "mlflow.db").write_text("x")
    existing.write_text("old + appended")
    stat = existing.stat()
    os.utime(existing, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    assert changed_files(tmp_path, before) == ["logs/godml.log", "mlflow.db"]


def test_ignores_caches_and_coverage_output(tmp_path):
    before = snapshot(tmp_path)
    for rel in (
        "__pycache__/m.cpython-311.pyc",
        ".pytest_cache/v/cache",
        ".mypy_cache/x.json",
        ".ruff_cache/x",
        "godml.egg-info/PKG-INFO",
        ".coverage",
        ".coverage.host.123",
        "coverage.xml",
    ):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    assert changed_files(tmp_path, before) == []


def test_no_changes(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    assert changed_files(tmp_path, snapshot(tmp_path)) == []
