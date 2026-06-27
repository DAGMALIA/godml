import pytest
import numpy as np
import pandas as pd
from godml.model_service.base_model_interface import BaseModel
from godml.model_service.model_registry.xgboost_model import XgboostModel
from godml.model_service.model_registry.random_forest_model import RandomForestModel


class TestXgboostModel:
    def test_inherits_base_model(self):
        assert issubclass(XgboostModel, BaseModel)
        assert isinstance(XgboostModel(), BaseModel)

    def test_initial_model_is_none(self):
        model = XgboostModel()
        assert model.model is None

    def test_train_returns_model_preds_metrics(self, binary_dataset):
        model = XgboostModel()
        ds = binary_dataset
        trained, preds, metrics = model.train(
            ds["X_train"], ds["y_train"],
            ds["X_test"], ds["y_test"],
            params={"n_estimators": 10, "max_depth": 2},
        )
        assert trained is not None
        assert len(preds) == len(ds["y_test"])
        assert isinstance(metrics, dict)
        assert len(metrics) > 0

    def test_preds_are_probabilities(self, binary_dataset):
        model = XgboostModel()
        ds = binary_dataset
        _, preds, _ = model.train(
            ds["X_train"], ds["y_train"],
            ds["X_test"], ds["y_test"],
            params={"n_estimators": 10},
        )
        assert all(0.0 <= p <= 1.0 for p in preds)

    def test_metrics_contain_auc(self, binary_dataset):
        model = XgboostModel()
        ds = binary_dataset
        _, _, metrics = model.train(
            ds["X_train"], ds["y_train"],
            ds["X_test"], ds["y_test"],
            params={"n_estimators": 10},
        )
        assert "auc" in metrics or "accuracy" in metrics

    def test_predict_after_train(self, binary_dataset):
        model = XgboostModel()
        ds = binary_dataset
        model.train(
            ds["X_train"], ds["y_train"],
            ds["X_test"], ds["y_test"],
            params={"n_estimators": 10},
        )
        preds = model.predict(ds["X_test"])
        assert len(preds) == len(ds["y_test"])
        assert all(0.0 <= p <= 1.0 for p in preds)

    def test_predict_before_train_raises(self, binary_dataset):
        model = XgboostModel()
        with pytest.raises(ValueError, match="no ha sido entrenado"):
            model.predict(binary_dataset["X_test"])

    def test_sanitize_params_eta_becomes_learning_rate(self):
        model = XgboostModel()
        params = {"eta": 0.05}
        result = model._sanitize_params(params)
        assert "learning_rate" in result
        assert result["learning_rate"] == 0.05
        assert "eta" not in result

    def test_sanitize_params_invalid_multi_class_removed(self):
        model = XgboostModel()
        params = {"multi_class": "bad_value"}
        result = model._sanitize_params(params)
        assert "multi_class" not in result

    def test_sanitize_params_valid_multi_class_kept(self):
        model = XgboostModel()
        params = {"multi_class": "ovr"}
        result = model._sanitize_params(params)
        assert "multi_class" in result

    def test_sanitize_params_merges_defaults(self):
        model = XgboostModel()
        params = {"max_depth": 4}
        result = model._sanitize_params(params)
        assert result["max_depth"] == 4
        assert "random_state" in result
        assert "n_estimators" in result

    def test_single_class_raises_value_error(self, binary_dataset):
        model = XgboostModel()
        ds = binary_dataset
        y_single = np.zeros(len(ds["y_train"]))
        y_test_single = np.zeros(len(ds["y_test"]))
        with pytest.raises(ValueError):
            model.train(ds["X_train"], y_single, ds["X_test"], y_test_single, {})


class TestRandomForestModel:
    def test_inherits_base_model(self):
        assert issubclass(RandomForestModel, BaseModel)
        assert isinstance(RandomForestModel(), BaseModel)

    def test_initial_model_is_none(self):
        model = RandomForestModel()
        assert model.model is None

    def test_train_returns_model_preds_metrics(self, binary_dataset):
        model = RandomForestModel()
        ds = binary_dataset
        trained, preds, metrics = model.train(
            ds["X_train"], ds["y_train"],
            ds["X_test"], ds["y_test"],
            params={"n_estimators": 10},
        )
        assert trained is not None
        assert len(preds) == len(ds["y_test"])
        assert isinstance(metrics, dict)

    def test_preds_are_probabilities(self, binary_dataset):
        model = RandomForestModel()
        ds = binary_dataset
        _, preds, _ = model.train(
            ds["X_train"], ds["y_train"],
            ds["X_test"], ds["y_test"],
            params={"n_estimators": 10},
        )
        assert all(0.0 <= p <= 1.0 for p in preds)

    def test_predict_after_train(self, binary_dataset):
        model = RandomForestModel()
        ds = binary_dataset
        model.train(
            ds["X_train"], ds["y_train"],
            ds["X_test"], ds["y_test"],
            params={"n_estimators": 10},
        )
        preds = model.predict(ds["X_test"])
        assert len(preds) == len(ds["y_test"])
        assert all(0.0 <= p <= 1.0 for p in preds)

    def test_predict_before_train_raises(self, binary_dataset):
        model = RandomForestModel()
        with pytest.raises(ValueError, match="no ha sido entrenado"):
            model.predict(binary_dataset["X_test"])

    def test_unknown_params_are_filtered(self, binary_dataset):
        model = RandomForestModel()
        ds = binary_dataset
        trained, preds, metrics = model.train(
            ds["X_train"], ds["y_train"],
            ds["X_test"], ds["y_test"],
            params={"n_estimators": 5, "totally_invalid_param": "garbage"},
        )
        assert trained is not None

    def test_defaults_applied_when_missing(self, binary_dataset):
        model = RandomForestModel()
        ds = binary_dataset
        # Pass empty params; DEFAULTS should fill in random_state etc.
        trained, preds, _ = model.train(
            ds["X_train"], ds["y_train"],
            ds["X_test"], ds["y_test"],
            params={},
        )
        assert trained is not None
        assert model.model.random_state == 42
