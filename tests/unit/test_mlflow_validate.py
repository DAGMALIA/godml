# test_mlflow_validate.py
"""
F1-03: MLflowExecutor.validate swallowed every exception from the governance
validator (`except Exception: pass`), so critical ValidationErrors (blank
owner, out-of-range metric threshold, batch deploy without output) never
blocked `godml run`.
"""

import pandas as pd
import pytest

from godml.compliance_service.validation_helpers import ValidationError
from godml.config_service.schema import PipelineDefinition
from godml.providers.mlflow import MLflowExecutor


@pytest.fixture
def valid_config(tmp_path, monkeypatch, minimal_pipeline_config):
    monkeypatch.chdir(tmp_path)
    data = tmp_path / "data.csv"
    pd.DataFrame({"x": [1, 2, 3, 4], "y": [0, 1, 0, 1]}).to_csv(data, index=False)
    config = dict(minimal_pipeline_config)
    config["dataset"] = {"uri": str(data), "hash": "auto", "target": "y"}
    return config


def validate(config: dict) -> None:
    MLflowExecutor(tracking_uri="sqlite:///mlflow.db").validate(
        PipelineDefinition(**config)
    )


def test_valid_pipeline_passes(valid_config):
    validate(valid_config)


def test_blank_owner_blocks(valid_config):
    valid_config["governance"] = {"owner": "   "}
    with pytest.raises(ValidationError, match="governance.owner"):
        validate(valid_config)


def test_out_of_range_threshold_blocks(valid_config):
    valid_config["metrics"] = [{"name": "auc", "threshold": 5.0}]
    with pytest.raises(ValidationError, match="auc"):
        validate(valid_config)


def test_batch_without_output_blocks(valid_config):
    valid_config["deploy"] = {"realtime": False, "batch_output": None}
    with pytest.raises(ValidationError, match="batch_output"):
        validate(valid_config)
