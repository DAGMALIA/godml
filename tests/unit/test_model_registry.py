"""Tests for model_registry, logistic_regression_model, auto_tuner."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


class TestLogisticRegressionModel:
    def _make_data(self):
        np.random.seed(42)
        X_train = pd.DataFrame(np.random.randn(60, 3), columns=["f1", "f2", "f3"])
        y_train = np.array([0] * 30 + [1] * 30)
        X_test = pd.DataFrame(np.random.randn(20, 3), columns=["f1", "f2", "f3"])
        y_test = np.array([0] * 10 + [1] * 10)
        return X_train, y_train, X_test, y_test

    def test_train_returns_model_and_metrics(self):
        from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel
        model = LogisticRegressionModel()
        X_train, y_train, X_test, y_test = self._make_data()
        fitted, y_pred, metrics = model.train(X_train, y_train, X_test, y_test, {})
        assert fitted is not None
        assert "accuracy" in metrics
        assert 0 <= metrics["accuracy"] <= 1

    def test_predict_after_train(self):
        from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel
        model = LogisticRegressionModel()
        X_train, y_train, X_test, _ = self._make_data()
        model.train(X_train, y_train, X_test, np.array([0] * 10 + [1] * 10), {})
        preds = model.predict(X_test)
        assert len(preds) == len(X_test)

    def test_max_iter_param(self):
        from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel
        model = LogisticRegressionModel()
        X_train, y_train, X_test, y_test = self._make_data()
        fitted, _, _ = model.train(X_train, y_train, X_test, y_test, {"max_iter": 200})
        assert fitted is not None


class TestModelRegistry:
    def test_registry_contains_known_models(self):
        from godml.model_service.model_registry.model_registry import model_registry
        assert "random_forest" in model_registry
        assert "xgboost" in model_registry
        assert "logistic_regression" in model_registry

    def test_registry_instantiable(self):
        from godml.model_service.model_registry.model_registry import model_registry
        cls = model_registry["random_forest"]
        instance = cls()
        assert instance is not None


class TestAutoTuner:
    def _labels(self, y):
        return np.array(y)

    def test_xgboost_binary(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(30, 2), columns=["a", "b"])
        y = self._labels([0, 1] * 15)
        params = auto_tune_hyperparameters("xgboost", {}, X, y)
        assert params["objective"] == "binary:logistic"

    def test_xgboost_multiclass(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(30, 2), columns=["a", "b"])
        y = self._labels([0, 1, 2] * 10)
        params = auto_tune_hyperparameters("xgboost", {}, X, y)
        assert params["objective"] == "multi:softprob"
        assert params["num_class"] == 3

    def test_xgboost_regression(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(30, 2), columns=["a", "b"])
        y = np.random.randn(30)
        params = auto_tune_hyperparameters("xgboost", {}, X, y)
        assert params["objective"] == "reg:squarederror"

    def test_random_forest_binary(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(20, 2), columns=["a", "b"])
        y = self._labels([0, 1] * 10)
        params = auto_tune_hyperparameters("random_forest", {}, X, y)
        assert "criterion" in params

    def test_random_forest_multiclass(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(30, 2), columns=["a", "b"])
        y = self._labels([0, 1, 2] * 10)
        params = auto_tune_hyperparameters("random_forest", {}, X, y)
        assert params["criterion"] == "gini"

    def test_logistic_regression_binary(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(20, 2), columns=["a", "b"])
        y = self._labels([0, 1] * 10)
        params = auto_tune_hyperparameters("logistic_regression", {}, X, y)
        assert params.get("solver") == "liblinear"

    def test_logistic_regression_multiclass(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(30, 2), columns=["a", "b"])
        y = self._labels([0, 1, 2] * 10)
        params = auto_tune_hyperparameters("logistic_regression", {}, X, y)
        assert params.get("solver") == "lbfgs"

    def test_unknown_model(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(20, 2), columns=["a", "b"])
        y = self._labels([0, 1] * 10)
        params = auto_tune_hyperparameters("unknown_model", {"foo": "bar"}, X, y)
        assert "foo" in params

    def test_removes_none_values(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(10, 2), columns=["a", "b"])
        y = self._labels([0, 1] * 5)
        params = auto_tune_hyperparameters("xgboost", {"null_param": None}, X, y)
        assert "null_param" not in params

    def test_removes_invalid_multi_class(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(10, 2), columns=["a", "b"])
        y = self._labels([0, 1] * 5)
        params = auto_tune_hyperparameters("xgboost", {"multi_class": "bad_value"}, X, y)
        assert "multi_class" not in params

    def test_pandas_series_y(self):
        from godml.model_service.auto_tuner import auto_tune_hyperparameters
        X = pd.DataFrame(np.random.randn(20, 2), columns=["a", "b"])
        y = pd.Series([0, 1] * 10)
        params = auto_tune_hyperparameters("random_forest", {}, X, y)
        assert isinstance(params, dict)
