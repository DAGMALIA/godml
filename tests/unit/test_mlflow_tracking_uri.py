# test_mlflow_tracking_uri.py
"""
F1-17: MLflowExecutor turns MLFLOW_TRACKING_URI=file:... into a sqlite store.
It did not create the directory (OperationalError when missing), stripped the
leading "/" of POSIX paths (file:///home/u/mlruns became cwd-relative) and
did not say it had switched backends.
"""

from pathlib import Path

import mlflow
import pytest

import godml.train.providers.mlflow as mlflow_provider
from godml.train.providers.mlflow import MLflowExecutor


@pytest.fixture
def info_log(monkeypatch):
    messages: list[str] = []
    monkeypatch.setattr(
        mlflow_provider.logger, "info", lambda msg, *a, **k: messages.append(str(msg))
    )
    return messages


@pytest.fixture
def elsewhere(tmp_path, monkeypatch):
    """Run from a different cwd so a cwd-relative path would land outside the store."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    return tmp_path


def test_file_uri_creates_missing_store_dir(elsewhere, monkeypatch, info_log):
    store = elsewhere / "not yet" / "mlruns"  # space: URI is percent-encoded
    monkeypatch.setenv("MLFLOW_TRACKING_URI", store.as_uri())

    MLflowExecutor()

    db = store / "mlflow.db"
    assert db.is_file()
    assert Path(mlflow.get_tracking_uri().removeprefix("sqlite:///")) == db
    # Nothing of the store may land under the cwd. (MLflow itself creates its
    # default artifact root ./mlruns there for sqlite backends; that is separate.)
    assert not (elsewhere / "cwd" / "not yet").exists()
    assert not list((elsewhere / "cwd").rglob("mlflow.db"))


def test_conversion_is_logged(elsewhere, monkeypatch, info_log):
    store = elsewhere / "mlruns"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", store.as_uri())

    MLflowExecutor()

    assert any(store.as_uri() in m and "sqlite:///" in m for m in info_log), info_log


def test_non_file_uri_is_used_as_is(elsewhere, monkeypatch):
    db = (elsewhere / "explicit.db").as_posix()
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)

    MLflowExecutor(tracking_uri=f"sqlite:///{db}")

    assert mlflow.get_tracking_uri() == f"sqlite:///{db}"
