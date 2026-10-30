# test_post_publish_smoke.py
"""
F1-24: every published version is smoke-tested from PyPI in a clean
environment, and a final X.Y.Z is only tagged after its latest RC passed.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


SMOKE = load("post_publish_smoke.yml")
RELEASE = load("release.yml")
STEPS = SMOKE["jobs"]["smoke"]["steps"]
RUNS = "\n".join(str(s.get("run", "")) for s in STEPS)


def test_runs_after_every_release_and_on_demand():
    # PyYAML reads the `on` key as True.
    on = SMOKE[True]
    assert on["workflow_run"]["workflows"] == [RELEASE["name"]]
    assert on["workflow_run"]["types"] == ["completed"]
    assert on["workflow_dispatch"]["inputs"]["version"]["required"] is True
    assert "workflow_run.conclusion == 'success'" in SMOKE["jobs"]["smoke"]["if"]


def test_run_name_carries_the_version_the_promotion_gate_looks_for():
    assert SMOKE["run-name"].startswith("Post-publish smoke ${{ inputs.version")


def test_installs_from_pypi_without_the_repository():
    assert not any("actions/checkout" in str(s.get("uses", "")) for s in STEPS)
    assert 'install --no-cache-dir "godml[all]==$VERSION"' in RUNS
    assert 'test "$INSTALLED" = "godml $VERSION"' in RUNS
    assert "${{" not in RUNS  # inputs only reach scripts through env


def test_exercises_the_cli_end_to_end():
    assert "godml --help" in RUNS
    assert "PYTHONIOENCODING=ascii godml --help" in RUNS
    assert "godml init demo" in RUNS
    assert "godml run -f godml.yml" in RUNS
    assert "test -s outputs/predictions.csv" in RUNS


def test_run_without_pii_key_must_fail_closed():
    step = next(s for s in STEPS if "without GODML_PII_KEY" in s.get("name", ""))
    assert "unset GODML_PII_KEY GODML_ALLOW_INSECURE_PII_KEY" in step["run"]
    assert 'grep -q "GODML_PII_KEY is required"' in step["run"]
    assert "exit 1" in step["run"]
    assert not step.get("continue-on-error")


def test_final_release_requires_green_rc_smoke_before_tagging():
    job = load("safety_scan.yml")["jobs"]["supplychain"]
    names = [s.get("name", "") for s in job["steps"]]
    gate = next(i for i, n in enumerate(names) if "post-publish smoke" in n)
    tag = next(i for i, n in enumerate(names) if "Tag and push" in n)
    assert gate < tag
    run = job["steps"][gate]["run"]
    assert "--workflow post_publish_smoke.yml" in run
    assert "--status success" in run
    assert 'grep -qxF -e "Post-publish smoke $RC"' in run
    assert not job["steps"][gate].get("continue-on-error")
    assert job["permissions"]["actions"] == "read"
