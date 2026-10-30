# test_import_contracts.py
"""
F2-13: pillar dependency contracts run in CI (lint-imports). Known
violations are listed as ignore_imports, each tagged with the open plan
task that removes it, and the list may only shrink.
"""

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
PLAN = (ROOT / "GODML_2_0_PLAN.md").read_text(encoding="utf-8")
CONTRACTS = tomllib.loads(PYPROJECT)["tool"]["importlinter"]["contracts"]

# Distinct violating imports when F2-13 landed. Lower it when one is fixed;
# never raise it.
MAX_IGNORED_IMPORTS = 8

IGNORE_LINE = re.compile(r'^\s*"(godml[\w.]* -> godml[\w.]*)",\s*# (F\d+-\d+)\s*$')


def ignore_lines() -> list[str]:
    block = PYPROJECT[PYPROJECT.index("[tool.importlinter]") :]
    lines, inside = [], False
    for line in block.splitlines():
        if line.startswith("ignore_imports = ["):
            inside = True
        elif inside and line.startswith("]"):
            inside = False
        elif inside:
            lines.append(line)
    return lines


def test_contracts_cover_every_pillar():
    sources = {c["source_modules"][0] for c in CONTRACTS}
    assert sources == {
        "godml.core",
        "godml.govern",
        "godml.train",
        "godml.serve",
        "godml.observe",
    }
    assert all(c["type"] == "forbidden" for c in CONTRACTS)


def test_ignored_imports_do_not_grow():
    distinct = {i for c in CONTRACTS for i in c.get("ignore_imports", [])}
    assert len(distinct) <= MAX_IGNORED_IMPORTS


def test_each_ignored_import_names_an_open_task():
    lines = ignore_lines()
    assert lines, "no ignore_imports found"
    for line in lines:
        match = IGNORE_LINE.match(line)
        assert match, f"ignore without task ID: {line.strip()}"
        task = match.group(2)
        status = re.search(rf"^- \*\*{task}\*\* (\S+)", PLAN, flags=re.MULTILINE)
        assert status, f"{task} is not a task in the plan"
        assert status.group(1) in {"⬜", "🟨"}, f"{task} is closed: drop its ignore"


def test_ci_runs_import_linter():
    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    runs = [str(s.get("run", "")) for s in ci["jobs"]["lint"]["steps"]]
    assert any(r.startswith("lint-imports") for r in runs)
