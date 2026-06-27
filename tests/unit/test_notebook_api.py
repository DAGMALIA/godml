import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from godml.notebook_api import (
    train_model,
    predict,
    evaluate,
    compare_models,
    apply_compliance,
    save_artifact,
    load_artifact,
    summarize_df,
    suggest_search_space,
    optimize_threshold,
)


class TestTrainModel:
    def test_xgboost_returns_model_wrapper(self, binary_dataset):
        ds = binary_dataset
        result = train_model(
            "xgboost", ds["X_train"], pd.Series(ds["y_train"]),
            hyperparams={"n_estimators": 10, "max_depth": 2},
        )
        assert hasattr(result, "model")
        assert result.model is not None

    def test_random_forest_returns_model_wrapper(self, binary_dataset):
        ds = binary_dataset
        result = train_model(
            "random_forest", ds["X_train"], pd.Series(ds["y_train"]),
            hyperparams={"n_estimators": 10},
        )
        assert hasattr(result, "model")
        assert result.model is not None

    def test_rf_alias_works(self, binary_dataset):
        ds = binary_dataset
        result = train_model("rf", ds["X_train"], pd.Series(ds["y_train"]), hyperparams={"n_estimators": 5})
        assert result.model is not None

    def test_xgb_alias_works(self, binary_dataset):
        ds = binary_dataset
        result = train_model("xgb", ds["X_train"], pd.Series(ds["y_train"]), hyperparams={"n_estimators": 5})
        assert result.model is not None

    def test_unsupported_model_raises(self, binary_dataset):
        ds = binary_dataset
        with pytest.raises(ValueError, match="no soportado"):
            train_model("nonexistent_model", ds["X_train"], pd.Series(ds["y_train"]))

    def test_train_without_hyperparams(self, binary_dataset):
        ds = binary_dataset
        result = train_model("random_forest", ds["X_train"], pd.Series(ds["y_train"]))
        assert result.model is not None


class TestPredict:
    def test_predict_returns_array_with_correct_length(self, binary_dataset):
        ds = binary_dataset
        result = train_model("random_forest", ds["X_train"], pd.Series(ds["y_train"]), hyperparams={"n_estimators": 5})
        preds = predict(result, ds["X_test"])
        assert preds is not None
        assert len(preds) == len(ds["X_test"])

    def test_predict_values_in_probability_range(self, binary_dataset):
        ds = binary_dataset
        result = train_model("xgboost", ds["X_train"], pd.Series(ds["y_train"]), hyperparams={"n_estimators": 5})
        preds = predict(result, ds["X_test"])
        assert all(0.0 <= p <= 1.0 for p in preds)

    def test_predict_accepts_raw_model(self, binary_dataset):
        ds = binary_dataset
        result = train_model("random_forest", ds["X_train"], pd.Series(ds["y_train"]), hyperparams={"n_estimators": 5})
        preds = predict(result.model, ds["X_test"])
        assert preds is not None


class TestEvaluate:
    def test_accuracy_metric(self, binary_dataset):
        y_true = binary_dataset["y_test"]
        y_pred = (np.random.rand(len(y_true)) > 0.5).astype(int)
        metrics = evaluate(y_true, y_pred, ["accuracy"])
        assert "accuracy" in metrics
        assert 0.0 <= metrics["accuracy"] <= 1.0

    def test_auc_metric(self, binary_dataset):
        y_true = binary_dataset["y_test"]
        y_prob = np.random.rand(len(y_true))
        metrics = evaluate(y_true, y_prob, ["auc"])
        assert "auc" in metrics
        assert 0.0 <= metrics["auc"] <= 1.0

    def test_multiple_metrics(self, binary_dataset):
        y_true = binary_dataset["y_test"]
        y_pred = (np.random.rand(len(y_true)) > 0.5).astype(int)
        metrics = evaluate(y_true, y_pred, ["accuracy", "f1"])
        assert "accuracy" in metrics
        assert "f1" in metrics

    def test_dict_input_for_metrics(self, binary_dataset):
        y_true = binary_dataset["y_test"]
        y_pred = (np.random.rand(len(y_true)) > 0.5).astype(int)
        metrics = evaluate(y_true, y_pred, {"accuracy": None})
        assert "accuracy" in metrics


class TestCompareModels:
    def test_empty_returns_empty_dataframe(self):
        result = compare_models([])
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_compares_two_models(self, binary_dataset):
        ds = binary_dataset
        r1 = train_model("xgboost", ds["X_train"], pd.Series(ds["y_train"]), hyperparams={"n_estimators": 5})
        r2 = train_model("random_forest", ds["X_train"], pd.Series(ds["y_train"]), hyperparams={"n_estimators": 5})
        df = compare_models([r1, r2])
        assert isinstance(df, pd.DataFrame)
        assert "model" in df.columns
        assert len(df) == 2

    def test_sorts_by_metric(self, binary_dataset):
        ds = binary_dataset
        r1 = train_model("xgboost", ds["X_train"], pd.Series(ds["y_train"]), hyperparams={"n_estimators": 5})
        r2 = train_model("random_forest", ds["X_train"], pd.Series(ds["y_train"]), hyperparams={"n_estimators": 5})
        df = compare_models([r1, r2], by="model")
        assert isinstance(df, pd.DataFrame)


class TestApplyCompliance:
    def test_pci_dss_returns_dataframe(self, pii_dataframe):
        result = apply_compliance(pii_dataframe, "pci-dss")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(pii_dataframe)

    def test_unknown_standard_returns_original(self, pii_dataframe):
        result = apply_compliance(pii_dataframe, "unknown-standard")
        assert result.equals(pii_dataframe)

    def test_pii_masked_under_pci_dss(self, pii_dataframe):
        result = apply_compliance(pii_dataframe, "pci-dss")
        original_email = pii_dataframe["email"].iloc[0]
        result_email = result["email"].iloc[0]
        assert original_email != result_email


class TestArtifacts:
    def test_save_and_load_dict(self, tmp_path):
        obj = {"key": "value", "score": 0.95}
        path = tmp_path / "artifact.pkl"
        save_artifact(obj, path)
        loaded = load_artifact(path)
        assert loaded == obj

    def test_save_and_load_array(self, tmp_path):
        arr = np.array([1, 2, 3, 4, 5])
        path = tmp_path / "array.pkl"
        save_artifact(arr, path)
        loaded = load_artifact(path)
        np.testing.assert_array_equal(loaded, arr)

    def test_load_creates_file(self, tmp_path):
        obj = "test string"
        path = tmp_path / "str.pkl"
        save_artifact(obj, path)
        assert path.exists()


class TestSummarizeDf:
    def test_returns_all_keys(self, pii_dataframe):
        s = summarize_df(pii_dataframe)
        assert "shape" in s
        assert "nulls" in s
        assert "dtypes" in s
        assert "unique" in s

    def test_shape_is_list(self, pii_dataframe):
        s = summarize_df(pii_dataframe)
        assert s["shape"] == list(pii_dataframe.shape)

    def test_nulls_counted_correctly(self):
        df = pd.DataFrame({"a": [1, None, 3], "b": [None, None, 1]})
        s = summarize_df(df)
        assert s["nulls"]["a"] == 1
        assert s["nulls"]["b"] == 2

    def test_unique_counts(self):
        df = pd.DataFrame({"cat": ["a", "b", "a", "c"]})
        s = summarize_df(df)
        assert s["unique"]["cat"] == 3

    def test_dtypes_are_strings(self, pii_dataframe):
        s = summarize_df(pii_dataframe)
        for v in s["dtypes"].values():
            assert isinstance(v, str)


class TestSuggestSearchSpace:
    def test_random_forest_has_n_estimators(self):
        space = suggest_search_space("random_forest")
        assert "n_estimators" in space
        assert isinstance(space["n_estimators"], list)

    def test_xgboost_has_learning_rate(self):
        space = suggest_search_space("xgboost")
        assert "learning_rate" in space
        assert isinstance(space["learning_rate"], list)

    def test_rf_alias(self):
        space = suggest_search_space("rf")
        assert "n_estimators" in space

    def test_xgb_alias(self):
        space = suggest_search_space("xgb")
        assert "n_estimators" in space

    def test_logistic_regression(self):
        space = suggest_search_space("logistic_regression")
        assert "C" in space

    def test_unknown_returns_empty(self):
        assert suggest_search_space("unknown_model") == {}

    def test_empty_string_returns_empty(self):
        assert suggest_search_space("") == {}


class TestOptimizeThreshold:
    def test_returns_tuple(self, binary_dataset):
        y_true = binary_dataset["y_test"]
        y_prob = np.random.rand(len(y_true))
        result = optimize_threshold(y_true, y_prob)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_threshold_in_range(self, binary_dataset):
        y_true = binary_dataset["y_test"]
        y_prob = np.random.rand(len(y_true))
        thr, _ = optimize_threshold(y_true, y_prob, metric="f1")
        assert 0.0 < thr < 1.0

    def test_score_in_range(self, binary_dataset):
        y_true = binary_dataset["y_test"]
        y_prob = np.random.rand(len(y_true))
        _, score = optimize_threshold(y_true, y_prob, metric="f1")
        assert 0.0 <= score <= 1.0

    def test_precision_metric(self, binary_dataset):
        y_true = binary_dataset["y_test"]
        y_prob = np.random.rand(len(y_true))
        thr, score = optimize_threshold(y_true, y_prob, metric="precision")
        assert isinstance(thr, float)
        assert isinstance(score, float)

    def test_recall_metric(self, binary_dataset):
        y_true = binary_dataset["y_test"]
        y_prob = np.random.rand(len(y_true))
        thr, score = optimize_threshold(y_true, y_prob, metric="recall")
        assert isinstance(thr, float)
