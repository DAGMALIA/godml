# monitoring_service/thresholds.py
# SPDX-License-Identifier: MIT
"""Metric threshold direction (F1-10). Pure Python: safe to import anywhere."""

from typing import Iterable, Mapping

# Loss metrics: lower is better, so the threshold is an upper bound.
LOWER_IS_BETTER = frozenset({"mse", "rmse", "mae", "log_loss"})


def lower_is_better(name: str) -> bool:
    return (name or "").strip().lower() in LOWER_IS_BETTER


def passes_threshold(name: str, value: float, threshold: float) -> bool:
    """`value <= threshold` for losses, `value >= threshold` otherwise."""
    return value <= threshold if lower_is_better(name) else value >= threshold


def comparison(name: str) -> str:
    return "<=" if lower_is_better(name) else ">="


def failed_thresholds(metrics: Iterable, values: Mapping[str, float]) -> list[str]:
    """One message per configured metric that was computed and misses its threshold."""
    failures = []
    for metric in metrics:
        value = values.get(metric.name)
        if value is None:
            continue
        if not passes_threshold(metric.name, value, metric.threshold):
            failures.append(
                f"{metric.name.upper()} ({value:.4f}) must be "
                f"{comparison(metric.name)} {metric.threshold}"
            )
    return failures


def register_condition_name(name: str) -> str:
    """SageMaker condition class that gates RegisterModel for this metric."""
    return (
        "ConditionLessThanOrEqualTo"
        if lower_is_better(name)
        else "ConditionGreaterThanOrEqualTo"
    )
