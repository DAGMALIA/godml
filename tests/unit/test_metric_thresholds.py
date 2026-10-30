# test_metric_thresholds.py
"""
F1-10: every threshold was read as "value >= threshold". For loss metrics
(mse, rmse, mae, log_loss) lower is better, so with `mse: 0.5` a model with
error 0.1 failed the gate and one with error 2.0 passed it.
"""

import pytest

from godml.govern.compliance.validation_helpers import validate_metrics
from godml.core.config.schema import Metric
from godml.govern.thresholds import (
    failed_thresholds,
    passes_threshold,
    register_condition_name,
)


@pytest.mark.parametrize(
    "name, value, threshold, expected",
    [
        ("mse", 0.1, 0.5, True),
        ("mse", 2.0, 0.5, False),
        ("RMSE", 0.3, 0.5, True),
        ("mae", 0.5, 0.5, True),
        ("log_loss", 0.40, 0.45, True),
        ("log_loss", 0.60, 0.45, False),
        ("auc", 0.90, 0.80, True),
        ("auc", 0.70, 0.80, False),
        ("r2", 0.80, 0.80, True),
        ("accuracy", 0.79, 0.80, False),
    ],
)
def test_passes_threshold(name, value, threshold, expected):
    assert passes_threshold(name, value, threshold) is expected


def test_failed_thresholds_reports_direction():
    metrics = [Metric(name="mse", threshold=0.5), Metric(name="auc", threshold=0.8)]
    failures = failed_thresholds(metrics, {"mse": 2.0, "auc": 0.9})
    assert len(failures) == 1
    assert "MSE" in failures[0] and "<=" in failures[0]


def test_missing_metric_is_not_a_failure():
    assert failed_thresholds([Metric(name="rmse", threshold=1.0)], {}) == []


@pytest.mark.parametrize(
    "name, expected",
    [("mse", "ConditionLessThanOrEqualTo"), ("auc", "ConditionGreaterThanOrEqualTo")],
)
def test_sagemaker_register_condition(name, expected):
    assert register_condition_name(name) == expected


def test_log_loss_threshold_is_not_limited_to_0_1():
    assert validate_metrics([Metric(name="log_loss", threshold=1.2)]) == []


def test_cli_table_marks_low_loss_as_passing(capsys):
    from godml.core.logger import print_metrics_table

    print_metrics_table({"mse": 0.1}, {"mse": 0.5})
    out = capsys.readouterr().out
    assert "✓" in out and "✗" not in out
