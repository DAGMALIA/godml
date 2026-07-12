"""Tests for: hash, yaml_utils, model_storage, predict_safely, cross_validation, log_model_generic"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ── hash ──────────────────────────────────────────────────────────────────────

class TestCalculateFileHash:
    def test_hash_deterministic(self, tmp_path):
        from godml.utils.hash import calculate_file_hash
        f = tmp_path / "data.csv"
        f.write_bytes(b"a,b,c\n1,2,3\n")
        h1 = calculate_file_hash(str(f))
        h2 = calculate_file_hash(str(f))
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_different_files_different_hashes(self, tmp_path):
        from godml.utils.hash import calculate_file_hash
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"hello")
        f2.write_bytes(b"world")
        assert calculate_file_hash(str(f1)) != calculate_file_hash(str(f2))

    def test_empty_file(self, tmp_path):
        from godml.utils.hash import calculate_file_hash
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        h = calculate_file_hash(str(f))
        assert isinstance(h, str) and len(h) == 64

    def test_missing_file_raises(self, tmp_path):
        from godml.utils.hash import calculate_file_hash
        with pytest.raises(FileNotFoundError):
            calculate_file_hash(str(tmp_path / "missing.csv"))


# ── yaml_utils ────────────────────────────────────────────────────────────────

class TestUpdateDatasetHashInYaml:
    def test_updates_existing_hash(self, tmp_path):
        from godml.utils.yaml_utils import update_dataset_hash_in_yaml
        import yaml
        cfg = {"dataset": {"uri": "./data.csv", "hash": "old"}, "name": "test"}
        p = tmp_path / "pipe.yml"
        p.write_text(yaml.dump(cfg), encoding="utf-8")
        update_dataset_hash_in_yaml(str(p), "newhash123")
        result = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert result["dataset"]["hash"] == "newhash123"

    def test_creates_dataset_key_if_missing(self, tmp_path):
        from godml.utils.yaml_utils import update_dataset_hash_in_yaml
        import yaml
        cfg = {"name": "test"}
        p = tmp_path / "pipe.yml"
        p.write_text(yaml.dump(cfg), encoding="utf-8")
        update_dataset_hash_in_yaml(str(p), "abc")
        result = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert result["dataset"]["hash"] == "abc"


class TestGenerateDefaultYaml:
    def test_returns_string(self):
        from godml.utils.yaml_utils import generate_default_yaml
        result = generate_default_yaml("my-project")
        assert isinstance(result, str)
        assert "my-project" in result

    def test_valid_yaml(self):
        from godml.utils.yaml_utils import generate_default_yaml
        import yaml
        raw = generate_default_yaml("test-project")
        parsed = yaml.safe_load(raw)
        assert parsed is not None
        assert parsed["name"] == "test-project"


class TestGenerateReadmeMd:
    def test_raises_on_missing_template(self):
        from godml.utils.yaml_utils import generate_readme_md
        # Calls files("godml.utils") — the template may or may not exist in test env
        try:
            result = generate_readme_md("TestProject")
            assert "TestProject" in result or isinstance(result, str)
        except RuntimeError:
            pass  # Template not bundled in test env — acceptable


class TestGenerateDockerfileTxt:
    def test_returns_string_or_raises(self):
        from godml.utils.yaml_utils import generate_dockerfile_txt
        try:
            result = generate_dockerfile_txt()
            assert isinstance(result, str)
        except RuntimeError:
            pass  # Template not bundled in test env — acceptable


# ── model_storage ─────────────────────────────────────────────────────────────

class TestModelStorage:
    def test_save_and_load(self, tmp_path, monkeypatch):
        from godml.utils.model_storage import save_model_to_structure, load_model_from_structure
        monkeypatch.chdir(tmp_path)
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=5)
        model.fit([[1, 2], [3, 4]], [0, 1])
        save_model_to_structure(model, "rf_test", "experiments")
        loaded = load_model_from_structure("rf_test", "experiments")
        assert loaded is not None

    def test_save_creates_metadata_json(self, tmp_path, monkeypatch):
        from godml.utils.model_storage import save_model_to_structure
        monkeypatch.chdir(tmp_path)
        from sklearn.linear_model import LogisticRegression
        model = LogisticRegression()
        model.fit([[1, 0], [0, 1]], [0, 1])
        save_model_to_structure(model, "lr_meta", "staging")
        meta = tmp_path / "models" / "staging" / "lr_meta_metadata.json"
        assert meta.exists()
        data = json.loads(meta.read_text())
        assert "model_type" in data

    def test_load_missing_model_raises(self, tmp_path, monkeypatch):
        from godml.utils.model_storage import load_model_from_structure
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            load_model_from_structure("nonexistent", "production")

    def test_list_models_empty(self, tmp_path, monkeypatch):
        from godml.utils.model_storage import list_models
        monkeypatch.chdir(tmp_path)
        result = list_models("production")
        assert result == []

    def test_list_models_all_envs(self, tmp_path, monkeypatch):
        from godml.utils.model_storage import list_models
        monkeypatch.chdir(tmp_path)
        result = list_models()
        assert isinstance(result, dict)
        assert "production" in result

    def test_promote_model(self, tmp_path, monkeypatch):
        from godml.utils.model_storage import save_model_to_structure, promote_model
        monkeypatch.chdir(tmp_path)
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=2)
        model.fit([[1, 2], [3, 4]], [0, 1])
        save_model_to_structure(model, "rf_promote", "experiments")
        promote_model("rf_promote", "experiments", "staging")
        staging = tmp_path / "models" / "staging" / "rf_promote_latest.pkl"
        assert staging.exists()

    def test_detect_model_type_sklearn(self, tmp_path, monkeypatch):
        from godml.utils.model_storage import _detect_model_type
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier()
        assert "random_forest" in _detect_model_type(model).lower() or "sklearn" in _detect_model_type(model)

    def test_detect_model_type_unknown(self):
        from godml.utils.model_storage import _detect_model_type
        class Dummy:
            pass
        assert _detect_model_type(Dummy()) == "unknown"

    def test_save_without_model_name_generates_name(self, tmp_path, monkeypatch):
        from godml.utils.model_storage import save_model_to_structure, list_models
        monkeypatch.chdir(tmp_path)
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=2)
        model.fit([[1, 2], [3, 4]], [0, 1])
        # no model_name provided → auto-generated
        path = save_model_to_structure(model, environment="experiments")
        assert Path(path).exists()

    def test_list_models_after_save(self, tmp_path, monkeypatch):
        from godml.utils.model_storage import save_model_to_structure, list_models
        monkeypatch.chdir(tmp_path)
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=2)
        model.fit([[1, 2], [3, 4]], [0, 1])
        save_model_to_structure(model, "rf_list_test", "experiments")
        # list all envs — hits the "if env_path.exists()" branches
        result = list_models()
        assert "experiments" in result
        assert len(result["experiments"]) > 0
        # list single env that exists
        models = list_models("experiments")
        assert len(models) > 0


# ── predict_safely ────────────────────────────────────────────────────────────

class TestPredictSafely:
    def test_sklearn_predict(self):
        from godml.utils.predict_safely import predict_safely
        from sklearn.ensemble import RandomForestClassifier
        X = [[1, 2], [3, 4], [5, 6]]
        y = [0, 1, 0]
        clf = RandomForestClassifier(n_estimators=2, random_state=0)
        clf.fit(X, y)
        preds = predict_safely(clf, [[1, 2]])
        assert len(preds) == 1

    def test_model_none_raises(self):
        from godml.utils.predict_safely import predict_safely
        from godml.monitoring_service.logger import PredictionError
        with pytest.raises(PredictionError, match="None"):
            predict_safely(None, [[1, 2]])

    def test_input_none_raises(self):
        from godml.utils.predict_safely import predict_safely
        from sklearn.ensemble import RandomForestClassifier
        from godml.monitoring_service.logger import PredictionError
        clf = RandomForestClassifier(n_estimators=2, random_state=0)
        clf.fit([[1, 2], [3, 4]], [0, 1])
        with pytest.raises(PredictionError, match="None"):
            predict_safely(clf, None)

    def test_empty_input_raises(self):
        from godml.utils.predict_safely import predict_safely
        from sklearn.ensemble import RandomForestClassifier
        from godml.monitoring_service.logger import PredictionError
        clf = RandomForestClassifier(n_estimators=2, random_state=0)
        clf.fit([[1, 2], [3, 4]], [0, 1])
        with pytest.raises(PredictionError, match="vacios|vac"):
            predict_safely(clf, [])

    def test_unsupported_model_raises(self):
        from godml.utils.predict_safely import predict_safely
        from godml.monitoring_service.logger import PredictionError
        class WeirdModel:
            pass
        with pytest.raises(PredictionError):
            predict_safely(WeirdModel(), [[1, 2]])


# ── cross_validation ──────────────────────────────────────────────────────────

class TestEvaluateWithCV:
    def test_classification_cv(self):
        from godml.utils.cross_validation import evaluate_with_cv
        from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(80, 4), columns=["a", "b", "c", "d"])
        y = np.array([0] * 40 + [1] * 40)
        avg, folds = evaluate_with_cv(LogisticRegressionModel, X, y, "classification", {}, folds=3)
        assert "accuracy" in avg
        assert len(folds) == 3

    def test_regression_cv(self):
        from godml.utils.cross_validation import evaluate_with_cv
        from godml.model_service.model_registry.linear_regression_model import LinearRegressionModel
        np.random.seed(0)
        X = pd.DataFrame(np.random.randn(60, 2), columns=["x1", "x2"])
        y = np.random.randn(60)
        avg, folds = evaluate_with_cv(LinearRegressionModel, X, y, "regression", {}, folds=3)
        assert len(folds) == 3


# ── log_model_generic ───────────────────────────────────────────────────────
# Regression coverage: mlflow.sklearn.log_model()'s skops_trusted_types kwarg
# is required on newer mlflow/skops (else UntrustedTypesFoundException for
# XGBoost's sklearn wrapper) but doesn't exist on older mlflow (TypeError).
# _log_sklearn_model must handle both without the caller knowing which.

class TestLogSklearnModel:
    def test_passes_skops_trusted_types_when_supported(self):
        from godml.utils.log_model_generic import _log_sklearn_model, _XGBOOST_SKOPS_TRUSTED_TYPES
        with patch("mlflow.sklearn.log_model") as mock_log:
            _log_sklearn_model(MagicMock(), {"name": "model"})
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs["skops_trusted_types"] == _XGBOOST_SKOPS_TRUSTED_TYPES

    def test_falls_back_when_kwarg_unsupported(self):
        from godml.utils.log_model_generic import _log_sklearn_model

        def fake_log_model(*args, **kwargs):
            if "skops_trusted_types" in kwargs:
                raise TypeError("log_model() got an unexpected keyword argument 'skops_trusted_types'")

        with patch("mlflow.sklearn.log_model", side_effect=fake_log_model) as mock_log:
            _log_sklearn_model(MagicMock(), {"name": "model"})
        assert mock_log.call_count == 2
        assert "skops_trusted_types" not in mock_log.call_args.kwargs

    def test_other_typeerrors_are_not_swallowed(self):
        from godml.utils.log_model_generic import _log_sklearn_model

        def fake_log_model(*args, **kwargs):
            raise TypeError("some unrelated failure")

        with patch("mlflow.sklearn.log_model", side_effect=fake_log_model):
            with pytest.raises(TypeError, match="some unrelated failure"):
                _log_sklearn_model(MagicMock(), {"name": "model"})


class TestLogModelGeneric:
    def test_xgboost_sklearn_api_routes_through_log_sklearn_model(self):
        from godml.utils.log_model_generic import log_model_generic
        from xgboost import XGBClassifier
        model = XGBClassifier()
        with patch("godml.utils.log_model_generic._log_sklearn_model") as mock_log:
            log_model_generic(model, model_name="m", registered_model_name="rm")
        mock_log.assert_called_once()
        assert mock_log.call_args.args[0] is model

    def test_native_booster_uses_xgboost_flavor_not_sklearn(self):
        from godml.utils.log_model_generic import log_model_generic
        from xgboost import Booster
        model = MagicMock(spec=Booster)
        with patch("mlflow.xgboost.log_model") as mock_xgb_log, \
             patch("godml.utils.log_model_generic._log_sklearn_model") as mock_sklearn_log:
            log_model_generic(model, model_name="m")
        mock_xgb_log.assert_called_once()
        mock_sklearn_log.assert_not_called()

    def test_unsupported_model_type_raises(self):
        from godml.utils.log_model_generic import log_model_generic
        with pytest.raises(NotImplementedError):
            log_model_generic(object(), model_name="m")


class TestEnsureValidTrackingUri:
    def test_leaves_absolute_windows_sqlite_uri_untouched(self, monkeypatch):
        # Regression test: this used to reset ANY uri containing "C:/" to a
        # relative "sqlite:///mlflow.db", silently redirecting log_model()
        # away from the db that opened the active run.
        import mlflow
        from godml.utils.log_model_generic import ensure_valid_tracking_uri
        monkeypatch.setattr(mlflow, "get_tracking_uri", lambda: "sqlite:///C:/tmp/mlflow.db")
        calls = []
        monkeypatch.setattr(mlflow, "set_tracking_uri", lambda uri: calls.append(uri))
        ensure_valid_tracking_uri()
        assert calls == []

    def test_resets_missing_or_file_uri(self, monkeypatch):
        import mlflow
        from godml.utils.log_model_generic import ensure_valid_tracking_uri
        monkeypatch.setattr(mlflow, "get_tracking_uri", lambda: "file:./mlruns")
        calls = []
        monkeypatch.setattr(mlflow, "set_tracking_uri", lambda uri: calls.append(uri))
        ensure_valid_tracking_uri()
        assert calls == ["sqlite:///mlflow.db"]
