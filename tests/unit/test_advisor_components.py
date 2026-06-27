"""Tests for advisor_service components (no gpt4all needed)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


class TestDataQualityJudge:
    def setup_method(self):
        from godml.advisor_service.data_quality_judge import DataQualityJudge
        self.judge = DataQualityJudge()

    def test_check_no_nulls(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        report = self.judge.check(df)
        assert report["nulls"]["a"] == 0
        assert report["duplicates"] == 0

    def test_check_with_nulls(self):
        df = pd.DataFrame({"a": [1, None, 3], "b": [None, "y", None]})
        report = self.judge.check(df)
        assert report["nulls"]["a"] == 1
        assert report["nulls"]["b"] == 2

    def test_check_with_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        report = self.judge.check(df)
        assert report["duplicates"] == 1

    def test_cardinality(self):
        df = pd.DataFrame({"category": ["a", "b", "a", "c"]})
        report = self.judge.check(df)
        assert report["cardinality"]["category"] == 3


class TestMetricJudge:
    def setup_method(self):
        from godml.advisor_service.metric_judge import MetricJudge
        self.judge = MetricJudge()

    def test_regression_task(self):
        np.random.seed(0)
        df = pd.DataFrame({"x": range(50), "target": np.random.randn(50)})
        result = self.judge.analyze(df, "target")
        assert result["task_type"] == "regression"
        assert "rmse" in result["metrics"]

    def test_binary_classification(self):
        df = pd.DataFrame({"x": range(20), "label": [0, 1] * 10})
        result = self.judge.analyze(df, "label")
        assert result["task_type"] == "binary_classification"
        assert "auc" in result["metrics"] or "f1" in result["metrics"]

    def test_multiclass_classification(self):
        df = pd.DataFrame({"x": range(30), "label": [0, 1, 2] * 10})
        result = self.judge.analyze(df, "label")
        assert result["task_type"] == "multiclass_classification"
        assert "accuracy" in result["metrics"]

    def test_imbalanced_binary(self):
        df = pd.DataFrame({"x": range(20), "label": [0] * 17 + [1] * 3})
        result = self.judge.analyze(df, "label")
        # imbalance detected → recall should be in metrics
        assert any(m in result["metrics"] for m in ["recall", "f1", "auc"])

    def test_pretty_print_doesnt_raise(self, capsys):
        df = pd.DataFrame({"x": range(10), "label": [0, 1] * 5})
        self.judge.analyze(df, "label", pretty=True)
        captured = capsys.readouterr()
        assert "Metric Judge" in captured.out

    def test_returns_recipe(self):
        df = pd.DataFrame({"x": range(10), "label": [0, 1] * 5})
        result = self.judge.analyze(df, "label")
        assert "recipe" in result
        assert "inputs" in result["recipe"]


class TestModelSelector:
    def setup_method(self):
        from godml.advisor_service.model_selector import ModelSelector
        self.selector = ModelSelector()

    def test_regression(self):
        models = self.selector.suggest("regression", 1000, 10)
        assert "linear_regression" in models or "random_forest" in models

    def test_binary_classification(self):
        models = self.selector.suggest("binary_classification", 500, 5)
        assert "xgboost" in models or "logistic_regression" in models

    def test_multiclass(self):
        models = self.selector.suggest("multiclass", 200, 8)
        assert "random_forest" in models or "xgboost" in models


class TestHyperparamAdvisor:
    def setup_method(self):
        from godml.advisor_service.hyperparam_advisor import HyperparamAdvisor
        self.advisor = HyperparamAdvisor()

    def test_random_forest_params(self):
        params = self.advisor.suggest("random_forest")
        assert "n_estimators" in params

    def test_xgboost_params(self):
        params = self.advisor.suggest("xgboost")
        assert "eta" in params

    def test_logistic_regression_params(self):
        params = self.advisor.suggest("logistic_regression")
        assert "C" in params

    def test_unknown_model(self):
        params = self.advisor.suggest("unknown_model")
        assert "note" in params
