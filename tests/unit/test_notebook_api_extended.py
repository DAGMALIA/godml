"""Extended tests for notebook_api: pipeline, training, artifacts, tuning."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ── pipeline (GodmlNotebook) ──────────────────────────────────────────────────

class TestGodmlNotebook:
    def test_create_pipeline_returns_definition(self):
        from godml.notebook_api.pipeline import GodmlNotebook
        nb = GodmlNotebook()
        pipe = nb.create_pipeline("my-pipe", "xgboost", {"max_depth": 3}, "./data.csv")
        assert pipe.name == "my-pipe"
        assert pipe.model.type == "xgboost"

    def test_create_pipeline_default_output(self):
        from godml.notebook_api.pipeline import GodmlNotebook
        nb = GodmlNotebook()
        pipe = nb.create_pipeline("test", "random_forest", {}, "./data.csv")
        assert "test" in pipe.deploy.batch_output

    def test_train_raises_without_pipeline(self):
        from godml.notebook_api.pipeline import GodmlNotebook
        nb = GodmlNotebook()
        with pytest.raises(ValueError, match="pipeline"):
            nb.train()

    def test_save_model_raises_without_model(self):
        from godml.notebook_api.pipeline import GodmlNotebook
        nb = GodmlNotebook()
        with pytest.raises(ValueError, match="modelo"):
            nb.save_model()

    def test_save_model_with_provided_model(self, tmp_path, monkeypatch):
        from godml.notebook_api.pipeline import GodmlNotebook
        from sklearn.ensemble import RandomForestClassifier
        monkeypatch.chdir(tmp_path)
        nb = GodmlNotebook()
        clf = RandomForestClassifier(n_estimators=2)
        clf.fit([[1, 2], [3, 4]], [0, 1])
        path = nb.save_model(model=clf, model_name="test_rf", environment="experiments")
        assert Path(path).exists()

    def test_train_from_yaml_missing_file_returns_error_string(self):
        from godml.notebook_api.pipeline import train_from_yaml
        result = train_from_yaml("/nonexistent/path.yml")
        assert "Error" in result

    def test_quick_train_yaml_missing_file(self):
        from godml.notebook_api.pipeline import quick_train_yaml
        result = quick_train_yaml("xgboost", {}, "/nonexistent/godml.yml")
        assert "Error" in result


# ── training (train_model, predict, evaluate, compare_models) ─────────────────

class TestTrainModel:
    def _dataset(self):
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(60, 4), columns=["a", "b", "c", "d"])
        y = pd.Series(np.array([0] * 30 + [1] * 30))
        return X, y

    def test_train_xgboost(self):
        from godml.notebook_api.training import train_model
        X, y = self._dataset()
        result = train_model("xgboost", X, y, {"max_depth": 3, "n_estimators": 10})
        assert result.model is not None

    def test_train_random_forest(self):
        from godml.notebook_api.training import train_model
        X, y = self._dataset()
        result = train_model("random_forest", X, y, {"n_estimators": 5})
        assert result.model is not None

    def test_train_logistic_regression(self):
        from godml.notebook_api.training import train_model
        X, y = self._dataset()
        result = train_model("logistic_regression", X, y, {})
        assert result.model is not None


class TestPredict:
    def test_predict_wrapper(self):
        from godml.notebook_api.training import train_model, predict
        import pandas as pd, numpy as np
        np.random.seed(0)
        X = pd.DataFrame(np.random.randn(40, 3), columns=["a", "b", "c"])
        y = pd.Series([0, 1] * 20)
        result = train_model("logistic_regression", X, y, {})
        preds = predict(result, X)
        assert len(preds) == len(X)

    def test_predict_with_raw_model(self):
        from godml.notebook_api.training import predict
        from sklearn.linear_model import LogisticRegression
        import pandas as pd, numpy as np
        clf = LogisticRegression()
        clf.fit([[1, 0], [0, 1], [1, 1], [0, 0]], [0, 1, 0, 1])
        preds = predict(clf, pd.DataFrame([[1, 0], [0, 1]], columns=["a", "b"]))
        assert len(preds) == 2


class TestCompareModels:
    def test_compare_empty(self):
        from godml.notebook_api.training import compare_models
        result = compare_models([])
        assert result.empty

    def test_compare_with_results(self):
        from godml.notebook_api.training import train_model, compare_models
        import pandas as pd, numpy as np
        np.random.seed(0)
        X = pd.DataFrame(np.random.randn(40, 3), columns=["a", "b", "c"])
        y = pd.Series([0, 1] * 20)
        r1 = train_model("logistic_regression", X, y, {})
        r2 = train_model("random_forest", X, y, {"n_estimators": 3})
        df = compare_models([r1, r2])
        assert "model" in df.columns


# ── artifacts ─────────────────────────────────────────────────────────────────

class TestArtifacts:
    def test_save_and_load_artifact(self, tmp_path):
        from godml.notebook_api.artifacts import save_artifact, load_artifact
        obj = {"key": "value", "num": 42}
        path = tmp_path / "artifact.pkl"
        save_artifact(obj, path)
        loaded = load_artifact(path)
        assert loaded == obj

    def test_summarize_df(self):
        from godml.notebook_api.artifacts import summarize_df
        df = pd.DataFrame({
            "a": [1, 2, None],
            "b": ["x", "y", "z"],
        })
        summary = summarize_df(df)
        assert summary["shape"] == [3, 2]
        assert summary["nulls"]["a"] == 1
        assert "b" in summary["dtypes"]
        assert summary["unique"]["b"] == 3

    def test_emit_lineage_silently_ignores_import_error(self):
        from godml.notebook_api.artifacts import emit_lineage
        # Should not raise even if openlineage is not installed
        emit_lineage("test_event", {"dataset": "my_data"})


# ── tuning ────────────────────────────────────────────────────────────────────

class TestTuning:
    def _dataset(self):
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(80, 4), columns=["a", "b", "c", "d"])
        y = pd.Series(np.array([0] * 40 + [1] * 40))
        return X, y

    def test_tune_model_random_forest(self):
        from godml.notebook_api.tuning import tune_model
        X, y = self._dataset()
        result = tune_model(
            "random_forest", X, y,
            search_space={"n_estimators": [3, 5], "max_depth": [2, 3]},
            cv=2, max_trials=2,
        )
        assert "best_params" in result
        assert "best_score" in result

    def test_tune_model_logistic_regression(self):
        from godml.notebook_api.tuning import tune_model
        X, y = self._dataset()
        result = tune_model(
            "logistic_regression", X, y,
            search_space={"C": [0.1, 1.0]},
            cv=2, max_trials=2,
        )
        assert "best_params" in result

    def test_tune_model_xgboost(self):
        from godml.notebook_api.tuning import tune_model
        X, y = self._dataset()
        result = tune_model(
            "xgboost", X, y,
            search_space={"n_estimators": [5, 10], "max_depth": [3]},
            cv=2, max_trials=2,
        )
        assert "best_estimator" in result

    def test_suggest_search_space_xgboost(self):
        from godml.notebook_api.tuning import suggest_search_space
        space = suggest_search_space("xgboost")
        assert "n_estimators" in space

    def test_suggest_search_space_unknown(self):
        from godml.notebook_api.tuning import suggest_search_space
        space = suggest_search_space("unknown")
        assert space == {}

    def test_optimize_threshold(self):
        from godml.notebook_api.tuning import optimize_threshold
        np.random.seed(0)
        y_true = np.array([0, 1] * 40)
        y_prob = np.random.rand(80)
        thr, score = optimize_threshold(y_true, y_prob, metric="f1")
        assert 0.0 < thr < 1.0
        assert 0.0 <= score <= 1.0

    def test_optimize_threshold_precision(self):
        from godml.notebook_api.tuning import optimize_threshold
        np.random.seed(1)
        y_true = np.array([0, 1] * 30)
        y_prob = np.random.rand(60)
        thr, score = optimize_threshold(y_true, y_prob, metric="precision")
        assert isinstance(thr, float)

    def test_optimize_threshold_recall(self):
        from godml.notebook_api.tuning import optimize_threshold
        np.random.seed(2)
        y_true = np.array([0, 1] * 30)
        y_prob = np.random.rand(60)
        thr, score = optimize_threshold(y_true, y_prob, metric="recall")
        assert isinstance(thr, float)
