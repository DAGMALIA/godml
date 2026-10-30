# test_safety_policy.py
"""
F0-16: Safety blocks CI with reviewed ignores only. The ignores in
.safety-policy.yml, the table in SECURITY.md, the workflows and the gate
script must agree, so the badge only ever reflects a blocking scan with
documented ignores.
"""

import datetime
import importlib.util
import json
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
    documented = set(
        re.findall(r"^\| ([A-Z0-9][A-Z0-9-]*) \|", table, flags=re.MULTILINE)
    )
    assert documented == set(policy_ignores())


@pytest.mark.parametrize("vid", sorted(policy_ignores()))
def test_each_ignore_has_reason_and_expiry_within_90_days(vid):
    entry = policy_ignores()[vid]
    assert len(entry["reason"]) >= 10
    # Safety compares `specifications` literally with the scanned specifier
    # ("==3.17.2"); a range like "mlflow>=2.13,<4" never matches, which made
    # both ignores inert in CI.
    assert "specifications" not in entry
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
def test_safety_is_blocking_and_gated_by_the_repo_policy(workflow):
    jobs = yaml.safe_load(
        (ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
    )["jobs"]
    steps = [s for job in jobs.values() for s in job.get("steps", [])]
    safety = [s for s in steps if "safety_gate.py" in str(s.get("run", ""))]
    assert len(safety) == 1, workflow
    step = safety[0]
    run = step["run"]
    assert not step.get("continue-on-error")
    assert "safety==3.3.1" in run
    assert "--policy-file .safety-policy.yml" in run
    assert "--target safety-scan" in run
    assert "--save-as json safety-report.json" in run
    assert "--policy .safety-policy.yml" in run
    assert '--safety-exit-code "${SAFETY_EXIT:-0}"' in run
    assert any("pip freeze" in str(s.get("run", "")) for s in steps)
    assert not any("pyupio/safety-action" in str(s.get("uses", "")) for s in steps)


# --- safety_gate.py -------------------------------------------------------


def load_gate():
    spec = importlib.util.spec_from_file_location(
        "safety_gate", ROOT / ".github" / "scripts" / "safety_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_gate()
TODAY = datetime.date(2026, 10, 30)


def make_report(deps: dict[str, list[str]]) -> dict:
    """deps: package name -> vulnerability ids found in it."""
    return {
        "scan_results": {
            "projects": [
                {
                    "files": [
                        {
                            "results": {
                                "dependencies": [
                                    {
                                        "name": name,
                                        "specifications": [
                                            {
                                                "raw": f"{name}==1.0",
                                                "vulnerabilities": {
                                                    "known_vulnerabilities": [
                                                        {"id": vid} for vid in vids
                                                    ]
                                                },
                                            }
                                        ],
                                    }
                                    for name, vids in deps.items()
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    }


def test_gate_accepts_only_reviewed_ignores():
    report = make_report({"mlflow": ["SFTY-1"], "skops": ["71782"], "numpy": []})
    ignores = {"SFTY-1": TODAY, "71782": TODAY}
    errors, notes = gate.evaluate(report, ignores, {"mlflow", "skops", "numpy"}, TODAY)
    assert errors == []
    assert len(notes) == 2


def test_gate_fails_on_unlisted_finding_even_if_safety_ignored_it():
    report = make_report({"mlflow": ["SFTY-1"]})
    vuln = report["scan_results"]["projects"][0]["files"][0]["results"]["dependencies"][
        0
    ]["specifications"][0]["vulnerabilities"]["known_vulnerabilities"][0]
    vuln["ignored"] = {"code": "manual", "reason": "cloud policy"}
    errors, _ = gate.evaluate(report, {}, {"mlflow"}, TODAY)
    assert errors and "SFTY-1" in errors[0]


def test_gate_fails_on_expired_ignore():
    report = make_report({"skops": ["71782"]})
    yesterday = TODAY - datetime.timedelta(days=1)
    errors, _ = gate.evaluate(report, {"71782": yesterday}, {"skops"}, TODAY)
    assert errors and "expired" in errors[0]


def test_gate_fails_when_a_frozen_package_was_not_scanned():
    report = make_report({"mlflow": []})
    errors, _ = gate.evaluate(report, {}, {"mlflow", "scikit-learn"}, TODAY)
    assert errors and "scikit-learn" in errors[0]


def test_gate_fails_when_nothing_was_frozen():
    errors, _ = gate.evaluate(make_report({}), {}, set(), TODAY)
    assert errors


def test_gate_reports_stale_ignores_without_failing():
    errors, notes = gate.evaluate(
        make_report({"mlflow": []}), {"71782": TODAY}, {"mlflow"}, TODAY
    )
    assert errors == []
    assert "no longer reported" in notes[0]


def test_frozen_packages_normalizes_names(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("# c\nScikit_Learn==1.5.0\nzope.interface==7.0\n\n", "utf-8")
    assert gate.frozen_packages(req) == {"scikit-learn", "zope-interface"}


def test_load_ignores_reads_the_repo_policy():
    ignores = gate.load_ignores(ROOT / ".safety-policy.yml")
    assert set(ignores) == set(policy_ignores())


@pytest.mark.parametrize("exit_code", [1, 2, 65])
def test_main_fails_closed_on_unexpected_safety_exit(tmp_path, exit_code):
    args = ["--report", str(tmp_path / "r.json"), "--policy", ".safety-policy.yml"]
    args += ["--requirements", str(tmp_path / "req.txt")]
    assert gate.main([*args, "--safety-exit-code", str(exit_code)]) == 1


def test_main_fails_closed_without_report(tmp_path):
    req = tmp_path / "req.txt"
    req.write_text("mlflow==3.17.2\n", encoding="utf-8")
    args = ["--report", str(tmp_path / "missing.json")]
    args += ["--policy", str(ROOT / ".safety-policy.yml")]
    args += ["--requirements", str(req), "--safety-exit-code", "64"]
    assert gate.main(args) == 1


def test_main_passes_with_reviewed_findings(tmp_path):
    req = tmp_path / "req.txt"
    req.write_text("mlflow==3.17.2\nskops==0.16.0\n", encoding="utf-8")
    report = tmp_path / "r.json"
    ids = sorted(policy_ignores())
    report.write_text(
        json.dumps(make_report({"mlflow": ids[:1], "skops": ids[1:]})),
        encoding="utf-8",
    )
    args = ["--report", str(report), "--policy", str(ROOT / ".safety-policy.yml")]
    args += ["--requirements", str(req), "--safety-exit-code", "64"]
    assert gate.main(args) == 0
