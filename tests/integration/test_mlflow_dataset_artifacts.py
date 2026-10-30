# test_mlflow_dataset_artifacts.py
"""
F1-02: MLflow must not receive the raw dataset. The executor used to upload
dataset.uri (the source CSV, before compliance) as a run artifact, leaking PII
even when PCI-DSS was configured. Only hash and schema are logged by default.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from godml.core.config.schema import PipelineDefinition
from godml.train.providers.mlflow import MLflowExecutor
from godml.govern.hash import calculate_file_hash

N_ROWS = 40
RAW_CARD = "4111111111111111"


def raw_emails() -> list[str]:
    return [f"person{i}@example.com" for i in range(N_ROWS)]


@pytest.fixture
def workspace(tmp_path, monkeypatch, minimal_pipeline_config):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)

    data = tmp_path / "data" / "customers.csv"
    data.parent.mkdir()
    pd.DataFrame(
        {
            "card_number": [RAW_CARD] * N_ROWS,
            "email": raw_emails(),
            "tenure": range(N_ROWS),
            "spend": [float(i % 7) for i in range(N_ROWS)],
            "churned": [i % 2 for i in range(N_ROWS)],
        }
    ).to_csv(data, index=False)

    def make_pipeline(**dataset_overrides) -> PipelineDefinition:
        config = dict(minimal_pipeline_config)
        config["dataset"] = {
            "uri": str(data),
            "hash": "auto",
            "target": "churned",
            **dataset_overrides,
        }
        config["governance"] = {
            "owner": "test@company.com",
            "compliance": "pci-dss",
            "policy": "mask_sensitive",
        }
        config["metrics"] = [{"name": "accuracy", "threshold": 0.0}]
        config["deploy"] = {"realtime": False, "batch_output": None}
        return PipelineDefinition(**config)

    return tmp_path, data, make_pipeline


def run(root: Path, pipeline: PipelineDefinition) -> None:
    MLflowExecutor(tracking_uri=f"sqlite:///{(root / 'mlflow.db').as_posix()}").run(
        pipeline
    )


def mlflow_files(root: Path) -> list[Path]:
    """Everything the run left on disk (tracking DB, artifacts, models) except the source CSV."""
    return [p for p in root.rglob("*") if p.is_file() and p.parent.name != "data"]


def find_artifact(root: Path, name: str) -> Path:
    matches = [p for p in mlflow_files(root) if p.name == name]
    assert matches, f"{name} not logged to MLflow"
    return matches[0]


def assert_no_raw_pii(root: Path) -> None:
    leaked = []
    for path in mlflow_files(root):
        content = path.read_bytes().decode("utf-8", errors="ignore")
        if RAW_CARD in content or any(e in content for e in raw_emails()):
            leaked.append(str(path.relative_to(root)))
    assert leaked == [], f"raw PII found in MLflow files: {leaked}"


def test_raw_dataset_is_not_uploaded(workspace):
    root, _, make_pipeline = workspace
    run(root, make_pipeline())
    assert not any(p.name == "customers.csv" for p in mlflow_files(root))
    assert_no_raw_pii(root)


def test_hash_and_schema_are_logged(workspace):
    root, data, make_pipeline = workspace
    run(root, make_pipeline())

    meta = json.loads(find_artifact(root, "dataset_metadata.json").read_text())
    assert meta["sha256"] == calculate_file_hash(str(data))
    assert meta["rows"] == N_ROWS
    assert set(meta["columns"]) == {
        "card_number",
        "email",
        "tenure",
        "spend",
        "churned",
    }
    assert "data" not in meta


def test_compliant_dataset_only_when_requested(workspace):
    root, _, make_pipeline = workspace
    run(root, make_pipeline(log_dataset=True))

    logged = pd.read_csv(find_artifact(root, "compliant_dataset.csv"), dtype=str)
    assert len(logged) == N_ROWS
    assert RAW_CARD not in set(logged["card_number"])
    assert_no_raw_pii(root)
