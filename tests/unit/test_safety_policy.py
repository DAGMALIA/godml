# test_safety_policy.py
"""
F0-16: Safety blocks CI with reviewed ignores only. The ignores in
.safety-policy.yml, the table in SECURITY.md and the workflows must agree,
so the badge only ever reflects a blocking scan with documented ignores.
"""

import datetime
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY = yaml.safe_load((ROOT / ".safety-policy.yml").read_text(encoding="utf-8"))
SECURITY = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
WORKFLOWS = ["ci.yml", "safety_scan.yml"]


def policy_ignores() -> dict:
    report = POLICY["report"]["dependency-vulnerabilities"]["auto-ignore-in-report"]
    return {str(k): v for k, v in report["vulnerabilities"].items()}


def test_security_md_lists_exactly_the_policy_ignores():
    table = SECURITY.split("**Safety:** exactly these ignores", 1)[1].split("\n\n", 2)[
        1
    ]
    documented = set(re.findall(r"^\| (\d+) \|", table, flags=re.MULTILINE))
    assert documented == set(policy_ignores())


@pytest.mark.parametrize("vid", sorted(policy_ignores()))
def test_each_ignore_has_reason_and_expiry_within_90_days(vid):
    entry = policy_ignores()[vid]
    assert len(entry["reason"]) >= 10
    expires = datetime.date.fromisoformat(str(entry["expires"]))
    reviewed = datetime.date(2026, 10, 25)
    assert (expires - reviewed).days <= 90


def test_policy_does_not_hide_findings():
    python = POLICY["report"]["dependency-vulnerabilities"]["auto-ignore-in-report"][
        "python"
    ]
    assert python["unpinned-requirements"] is False
    assert python["environment-results"] is False
    fail = POLICY["fail-scan-with-exit-code"]["dependency-vulnerabilities"]
    assert fail["enabled"] is True
    assert {"critical", "high", "medium", "low"} <= set(
        fail["fail-on-any-of"]["cvss-severity"]
    )


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_safety_is_blocking_and_uses_the_policy(workflow):
    jobs = yaml.safe_load(
        (ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
    )["jobs"]
    steps = [s for job in jobs.values() for s in job.get("steps", [])]
    safety = [s for s in steps if "pyupio/safety-action" in str(s.get("uses", ""))]
    assert len(safety) == 1, workflow
    step = safety[0]
    assert not step.get("continue-on-error")
    assert "--policy-file .safety-policy.yml" in step["with"]["args"]
    assert "--target safety-scan" in step["with"]["args"]
    assert any("pip freeze" in str(s.get("run", "")) for s in steps)
