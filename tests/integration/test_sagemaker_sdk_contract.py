# test_sagemaker_sdk_contract.py
"""
F1-22 / F1-23: run against the real SageMaker SDK (installed through the
`test-aws` extra). With `sagemaker<4` a fresh install got SDK v3, where
none of these modules exist, and nothing noticed because no test imported
the SDK. The loss-metric RegisterModel condition is also built for real.
"""

import importlib

import pytest

# Every SDK name godml imports (providers/sagemaker); keep in sync with
# `git grep "from sagemaker" godml`.
SDK_NAMES = [
    ("sagemaker", "image_uris"),
    ("sagemaker.inputs", "TrainingInput"),
    ("sagemaker.processing", "ScriptProcessor"),
    ("sagemaker.processing", "ProcessingInput"),
    ("sagemaker.processing", "ProcessingOutput"),
    ("sagemaker.sklearn", "SKLearn"),
    ("sagemaker.xgboost", "XGBoost"),
    ("sagemaker.workflow.condition_step", "ConditionStep"),
    ("sagemaker.workflow.conditions", "ConditionLessThanOrEqualTo"),
    ("sagemaker.workflow.conditions", "ConditionGreaterThanOrEqualTo"),
    ("sagemaker.workflow.functions", "JsonGet"),
    ("sagemaker.workflow.pipeline", "Pipeline"),
    ("sagemaker.workflow.pipeline_context", "PipelineSession"),
    ("sagemaker.workflow.properties", "PropertyFile"),
    ("sagemaker.workflow.step_collections", "RegisterModel"),
    ("sagemaker.workflow.steps", "ProcessingStep"),
    ("sagemaker.workflow.steps", "TrainingStep"),
]


@pytest.fixture(autouse=True)
def quiet_v2_notice(monkeypatch):
    monkeypatch.setenv("SAGEMAKER_SUPPRESS_V2_WARNING", "1")


@pytest.mark.parametrize("module, name", SDK_NAMES, ids=lambda v: str(v))
def test_sdk_exposes_what_godml_uses(module, name):
    assert hasattr(importlib.import_module(module), name)


@pytest.mark.parametrize(
    "metric, threshold, expected_type",
    [("mse", 0.5, "LessThanOrEqualTo"), ("auc", 0.8, "GreaterThanOrEqualTo")],
)
def test_real_register_condition(metric, threshold, expected_type):
    from sagemaker.workflow import conditions
    from sagemaker.workflow.functions import JsonGet
    from sagemaker.workflow.properties import PropertyFile

    from godml.govern.thresholds import register_condition_name

    report = PropertyFile(
        name="EvaluationReport", output_name="evaluation", path="evaluation.json"
    )
    condition = getattr(conditions, register_condition_name(metric))(
        left=JsonGet(step_name="Evaluation", property_file=report, json_path=metric),
        right=threshold,
    )
    request = condition.to_request()
    assert request["Type"] == expected_type
    assert request["RightValue"] == threshold
