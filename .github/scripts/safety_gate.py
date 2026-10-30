"""Safety gate (F0-16): the repository decides which findings are accepted.

`safety scan` always applies the policy stored in Safety Platform when the
project has one, and the platform rejects some vulnerability IDs (e.g.
`SFTY-...`), so the reviewed ignores in `.safety-policy.yml` cannot be
enforced there. This gate reads the JSON report of the scan and fails
unless every finding is listed in `.safety-policy.yml` with an expiry that
has not passed. Whatever Safety itself marked as ignored is not trusted.

Fail-closed: a missing or unreadable report, an unexpected Safety exit
code, or a frozen package that the report does not cover all fail the gate.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

# Exit codes of `safety scan`: clean, and vulnerabilities found.
SAFETY_OK = (0, 64)


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_ignores(policy_path: Path) -> dict[str, datetime.date]:
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    report = policy["report"]["dependency-vulnerabilities"]["auto-ignore-in-report"]
    ignores = {}
    for vid, entry in (report.get("vulnerabilities") or {}).items():
        ignores[str(vid)] = datetime.date.fromisoformat(str(entry["expires"]))
    return ignores


def frozen_packages(requirements: Path) -> set[str]:
    names = set()
    for line in requirements.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(normalize(re.split(r"[=<>~!@ ;\[]", line, maxsplit=1)[0]))
    return names


def report_dependencies(report: dict[str, Any]) -> list[dict[str, Any]]:
    deps = []
    for project in report["scan_results"]["projects"]:
        for file in project["files"]:
            deps.extend(file["results"]["dependencies"])
    return deps


def findings(report: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(vulnerability id, package, specification) for every known finding."""
    found = []
    for dep in report_dependencies(report):
        for spec in dep["specifications"]:
            for vuln in spec["vulnerabilities"]["known_vulnerabilities"]:
                found.append((str(vuln["id"]), dep["name"], spec["raw"]))
    return found


def evaluate(
    report: dict[str, Any],
    ignores: dict[str, datetime.date],
    frozen: set[str],
    today: datetime.date,
) -> tuple[list[str], list[str]]:
    """Return (errors, notes). The gate passes only without errors."""
    errors = []
    notes = []

    scanned = {normalize(dep["name"]) for dep in report_dependencies(report)}
    missing = sorted(frozen - scanned)
    if not frozen:
        errors.append("the frozen requirements are empty; nothing was scanned")
    if missing:
        errors.append(f"packages frozen but not in the report: {', '.join(missing)}")

    seen = set()
    for vid, package, spec in findings(report):
        seen.add(vid)
        expires = ignores.get(vid)
        if expires is None:
            errors.append(f"{vid} in {spec} is not accepted in .safety-policy.yml")
        elif expires < today:
            errors.append(f"{vid} in {spec}: the ignore expired on {expires}")
        else:
            notes.append(f"{vid} in {spec} accepted until {expires}")

    for vid in sorted(set(ignores) - seen):
        notes.append(f"{vid} is ignored in .safety-policy.yml but no longer reported")
    return errors, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--safety-exit-code", type=int, required=True)
    args = parser.parse_args(argv)

    if args.safety_exit_code not in SAFETY_OK:
        print(f"::error::Safety did not complete (exit {args.safety_exit_code})")
        return 1
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        errors, notes = evaluate(
            report,
            load_ignores(args.policy),
            frozen_packages(args.requirements),
            datetime.date.today(),
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"::error::Cannot evaluate the Safety report: {exc!r}")
        return 1

    for note in notes:
        print(note)
    for error in errors:
        print(f"::error::{error}")
    if errors:
        return 1
    print("Safety gate passed: every finding is a reviewed ignore.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
