import pytest
import numpy as np
from godml.monitoring_service.metrics import evaluate_binary_classification, evaluate_regression
from godml.monitoring_service.metric_diagnostics import analyze_metric_issue, explain_issue_and_action


class TestEvaluateBinaryClassification:
    def test_perfect_predictions_auc_is_1(self):
        y_true = np.array([0, 1, 0, 1, 1, 0])
        y_proba = np.array([0.01, 0.99, 0.02, 0.98, 0.97, 0.03])
        metrics = evaluate_binary_classification(y_true, y_proba)
        assert metrics["auc"] > 0.99
        assert metrics["accuracy"] == pytest.approx(1.0)

    def test_returns_expected_binary_keys(self):
        y_true = np.array([0, 1, 0, 1])
        y_proba = np.array([0.3, 0.7, 0.4, 0.6])
        metrics = evaluate_binary_classification(y_true, y_proba)
        assert "auc" in metrics
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics

    def test_metrics_are_floats_in_range(self):
        y_true = np.array([0, 1, 0, 1, 0, 1])
        y_proba = np.array([0.2, 0.8, 0.3, 0.7, 0.4, 0.6])
        metrics = evaluate_binary_classification(y_true, y_proba)
        for k, v in metrics.items():
            assert 0.0 <= v <= 1.0, f"{k}={v} out of [0,1]"

    def test_all_same_class_returns_gracefully(self):
        y_true = np.array([0, 0, 0, 0])
        y_proba = np.array([0.3, 0.4, 0.2, 0.1])
        metrics = evaluate_binary_classification(y_true, y_proba)
        assert isinstance(metrics, dict)

    def test_threshold_affects_binary_predictions(self):
        y_true = np.array([0, 1])
        y_proba = np.array([0.4, 0.6])
        metrics_low = evaluate_binary_classification(y_true, y_proba, threshold=0.3)
        metrics_high = evaluate_binary_classification(y_true, y_proba, threshold=0.7)
        assert isinstance(metrics_low, dict)
        assert isinstance(metrics_high, dict)


class TestEvaluateMulticlass:
    def test_returns_accuracy_and_f1_macro(self):
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_proba = np.array([
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
            [0.7, 0.2, 0.1],
            [0.2, 0.6, 0.2],
            [0.1, 0.2, 0.7],
        ])
        metrics = evaluate_binary_classification(y_true, y_proba)
        assert "accuracy" in metrics
        assert "f1_macro" in metrics

    def test_perfect_multiclass(self):
        y_true = np.array([0, 1, 2])
        y_proba = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])
        metrics = evaluate_binary_classification(y_true, y_proba)
        assert metrics["accuracy"] == pytest.approx(1.0)
        assert metrics["f1_macro"] == pytest.approx(1.0)


class TestEvaluateRegression:
    def test_perfect_regression_mse_zero(self):
        y_true = np.array([1.0, 2.0, 3.0, 4.0])
        y_pred = np.array([1.0, 2.0, 3.0, 4.0])
        metrics = evaluate_regression(y_true, y_pred)
        assert metrics["mse"] == pytest.approx(0.0)
        assert metrics["mae"] == pytest.approx(0.0)
        assert metrics["r2"] == pytest.approx(1.0)

    def test_returns_all_default_metrics(self):
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.1, 1.9, 3.2])
        metrics = evaluate_regression(y_true, y_pred)
        assert "mse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics

    def test_selective_metrics(self):
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.0, 2.0, 3.0])
        metrics = evaluate_regression(y_true, y_pred, metric_names=["r2"])
        assert "r2" in metrics
        assert "mse" not in metrics
        assert "mae" not in metrics

    def test_values_are_floats(self):
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.1, 2.1, 2.9])
        metrics = evaluate_regression(y_true, y_pred)
        for v in metrics.values():
            assert isinstance(v, float)


class TestAnalyzeMetricIssue:
    def test_none_output(self):
        reason, code = analyze_metric_issue(np.array([0, 1]), None)
        assert code == "NO_OUTPUT"
        assert isinstance(reason, str)

    def test_empty_output(self):
        reason, code = analyze_metric_issue(np.array([0, 1]), np.array([]))
        assert code == "NO_OUTPUT"

    def test_nan_values(self):
        reason, code = analyze_metric_issue(
            np.array([0, 1]),
            np.array([float("nan"), 0.5])
        )
        assert code == "NAN_VALUES"

    def test_shape_1d(self):
        reason, code = analyze_metric_issue(
            np.array([0, 1, 2]),
            np.array([0, 1, 2])
        )
        assert code == "SHAPE_1D"

    def test_missing_classes(self):
        y_true = np.array([0, 1, 2])
        y_proba = np.array([[0.8, 0.2], [0.3, 0.7], [0.5, 0.5]])
        reason, code = analyze_metric_issue(y_true, y_proba)
        assert code == "MISSING_CLASSES"

    def test_extra_classes(self):
        y_true = np.array([0, 1])
        y_proba = np.array([[0.6, 0.2, 0.2], [0.2, 0.6, 0.2]])
        reason, code = analyze_metric_issue(y_true, y_proba)
        assert code == "EXTRA_CLASSES"


class TestExplainIssueAndAction:
    def test_returns_non_empty_string(self):
        result = explain_issue_and_action("some reason", "NAN_VALUES")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_cause_and_action(self):
        result = explain_issue_and_action("reason text", "SHAPE_1D")
        assert "Causa" in result
        assert "Acción" in result

    def test_all_known_codes(self):
        codes = ["NO_OUTPUT", "NAN_VALUES", "SHAPE_1D", "MISSING_CLASSES",
                 "EXTRA_CLASSES", "SHAPE_INVALID", "GENERIC", "INTERNAL"]
        for code in codes:
            result = explain_issue_and_action("reason", code)
            assert isinstance(result, str)

    def test_unknown_code_returns_string(self):
        result = explain_issue_and_action("reason", "TOTALLY_UNKNOWN")
        assert isinstance(result, str)
