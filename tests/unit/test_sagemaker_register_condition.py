# test_sagemaker_register_condition.py
"""
F1-22: build_register_step gates RegisterModel on the primary metric. F1-10
made the condition direction-aware (<= for losses) but it was never run: the
SageMaker SDK is not installed in the test environments. These tests replace
the four SDK modules the function imports with recorders.
"""

import sys
import types

import pytest

from godml.core.config.schema import PipelineDefinition
from godml.train.providers.sagemaker.step_builder import build_register_step


class Recorder:
    """Stands in for an SDK class: stores its kwargs, records its own name."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def recorder(name: str) -> type:
    return type(name, (Recorder,), {})


@pytest.fixture
def fake_sdk(monkeypatch):
    conditions = types.ModuleType("sagemaker.workflow.conditions")
    for name in ("ConditionGreaterThanOrEqualTo", "ConditionLessThanOrEqualTo"):
        setattr(conditions, name, recorder(name))
    modules = {
        "sagemaker": types.ModuleType("sagemaker"),
        "sagemaker.workflow": types.ModuleType("sagemaker.workflow"),
        "sagemaker.workflow.conditions": conditions,
        "sagemaker.workflow.step_collections": types.ModuleType("step_collections"),
        "sagemaker.workflow.condition_step": types.ModuleType("condition_step"),
        "sagemaker.workflow.functions": types.ModuleType("functions"),
    }
    modules["sagemaker.workflow.step_collections"].RegisterModel = recorder(
        "RegisterModel"
    )
    modules["sagemaker.workflow.condition_step"].ConditionStep = recorder(
        "ConditionStep"
    )
    modules["sagemaker.workflow.functions"].JsonGet = recorder("JsonGet")
    modules["sagemaker.workflow"].conditions = conditions
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)


class TrainingStep:
    estimator = object()

    class properties:
        class ModelArtifacts:
            S3ModelArtifacts = "s3://bucket/model.tar.gz"


class EvaluationStep:
    name = "Evaluation"


def register_step(minimal_pipeline_config, metric: str, threshold: float):
    config = dict(minimal_pipeline_config)
    config["metrics"] = [{"name": metric, "threshold": threshold}]
    config["registry"] = {"model_package_group": "churn", "approval": "manual"}
    return build_register_step(
        PipelineDefinition(**config), TrainingStep(), EvaluationStep(), "report"
    )


@pytest.mark.parametrize(
    "metric, threshold, expected",
    [
        ("mse", 0.5, "ConditionLessThanOrEqualTo"),
        ("rmse", 1.2, "ConditionLessThanOrEqualTo"),
        ("mae", 0.3, "ConditionLessThanOrEqualTo"),
        ("log_loss", 0.45, "ConditionLessThanOrEqualTo"),
        ("auc", 0.8, "ConditionGreaterThanOrEqualTo"),
        ("accuracy", 0.9, "ConditionGreaterThanOrEqualTo"),
    ],
)
def test_condition_direction(
    fake_sdk, minimal_pipeline_config, metric, threshold, expected
):
    step = register_step(minimal_pipeline_config, metric, threshold)
    assert type(step).__name__ == "ConditionStep"
    (condition,) = step.kwargs["conditions"]
    assert type(condition).__name__ == expected
    assert condition.kwargs["right"] == threshold
    left = condition.kwargs["left"]
    assert left.kwargs["json_path"] == metric
    assert left.kwargs["step_name"] == "Evaluation"
    assert [type(s).__name__ for s in step.kwargs["if_steps"]] == ["RegisterModel"]
