# test_readme.py
"""
F1-14: the README only documents what exists and works ("No documentar lo que
no existe", CLAUDE.md). Its Python and YAML examples are executed; the CLI
commands, extras and model types it lists must exist; unimplemented
compliance standards must not be advertised.
"""

import re
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "godml" / "utils" / "README_TEMPLATE.txt").read_text(
    encoding="utf-8"
)

# Blocks that cannot run in the test environment, with the reason.
NOT_EXECUTED = {
    "advisor_full_report": "needs godml[advisor] (gpt4all + a downloaded local model)",
}


def code_blocks(lang: str) -> list[str]:
    return re.findall(rf"```{lang}\n(.*?)```", README, flags=re.DOTALL)


@pytest.fixture
def churn_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    rng = np.random.default_rng(0)
    n = 400
    df = pd.DataFrame(
        {
            "tenure": rng.integers(1, 72, n),
            "monthly_spend": rng.normal(60, 15, n).round(2),
            "plan": rng.choice(["basic", "pro", "family"], n),
        }
    )
    df["churn"] = ((df["tenure"] < 24) ^ (rng.random(n) < 0.02)).astype(int)
    (tmp_path / "data").mkdir()
    df.to_csv(tmp_path / "data" / "churn.csv", index=False)
    return tmp_path


@pytest.mark.parametrize("word", ["GDPR", "HIPAA", "SOX"])
def test_unimplemented_standards_are_not_advertised(word):
    assert not re.search(rf"\b{word}\b", README)
    assert not re.search(rf"\b{word}\b", TEMPLATE)


def test_template_does_not_impose_a_license_or_old_python():
    assert "License" not in TEMPLATE
    assert "3.8" not in TEMPLATE


def test_python_examples_run(churn_project):
    namespace: dict = {}
    executed = 0
    for block in code_blocks("python"):
        if any(marker in block for marker in NOT_EXECUTED):
            continue
        exec(compile(block, "README.md", "exec"), namespace)  # noqa: S102
        executed += 1
    assert executed >= 4


def test_yaml_example_runs(churn_project):
    from godml.core_service.parser import load_pipeline
    from godml.providers.mlflow import MLflowExecutor

    (churn_project / "godml.yml").write_text(code_blocks("yaml")[0], encoding="utf-8")
    pipeline = load_pipeline("godml.yml")
    assert pipeline.dataset.target == "churn"
    executor = MLflowExecutor()
    executor.validate(pipeline)
    executor.run(pipeline)


def test_cli_reference_matches_real_commands():
    from typer.main import get_command

    from godml.cli.app import app

    section = README.split("## CLI reference", 1)[1].split("\n## ", 1)[0]
    documented = set(re.findall(r"^godml ([a-z][a-z-]*)", section, flags=re.MULTILINE))
    real = set(get_command(app).commands)
    assert documented == real, (documented, real)
    assert "godml --version" in section


def test_installation_extras_exist():
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["optional-dependencies"]
    section = README.split("## Installation", 1)[1].split("\n## ", 1)[0]
    documented = set(re.findall(r"godml\[([a-z-]+)\]", section))
    assert documented and documented <= set(extras), documented - set(extras)


def test_supported_model_types_exist():
    from godml.model_service.model_loader import CORE_MODEL_REGISTRY as CORE_MODELS

    section = README.split("### Supported model types", 1)[1].split("\n## ", 1)[0]
    documented = set(re.findall(r"^\| `([a-z_]+)` \|", section, flags=re.MULTILINE))
    assert documented and documented <= set(CORE_MODELS), documented - set(CORE_MODELS)


def test_init_yaml_names_a_target():
    """Quick start: `godml init` must produce a YAML with dataset.target."""
    import yaml

    from godml.utils.yaml_utils import generate_default_yaml

    config = yaml.safe_load(generate_default_yaml("demo"))
    assert config["dataset"]["target"]
