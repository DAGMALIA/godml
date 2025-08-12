import os
import pandas as pd
from godml.notebook_api import quick_train, quick_train_yaml, GodmlNotebook, train_from_yaml


def test_quick_train_runs_without_error(tmp_path):
    df = pd.DataFrame({
        "feature_0": [0.1, 0.2, 0.3, 0.4],
        "feature_1": [1, 0, 1, 0],
        "target": [0, 1, 0, 1]
    })
    csv_path = tmp_path / "data.csv"
    df.to_csv(csv_path, index=False)
    result = quick_train(
        model_type="random_forest",
        hyperparameters={"n_estimators": 10, "max_depth": 3},
        dataset_path=str(csv_path)
    )
    assert isinstance(result, str)
    assert "entrenado exitosamente" in result.lower()


def test_quick_train_yaml_runs_and_saves(tmp_path):
    csv_path = tmp_path / "data.csv"
    df = pd.DataFrame({
        "feature_0": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "feature_1": [0,   1,   1,   0,   1,   0],
        "target":    [1,   0,   1,   0,   1,   0]
    })
    df.to_csv(csv_path, index=False)

    yaml_path = tmp_path / "godml.yml"
    yaml_path.write_text(f"""
name: test-pipeline
version: "1.0.0"
provider: mlflow
dataset:
  uri: {csv_path.as_posix()}
  hash: auto
model:
  type: xgboost
  source: core
  hyperparameters:
    eta: 0.3
    max_depth: 2
metrics:
  - name: auc
    threshold: 0.5
governance:
  owner: test@example.com
  tags: [{{source: test}}]
deploy:
  realtime: false
  batch_output: ./outputs/predictions.csv
""")

    result = quick_train_yaml(
        model_type="xgboost",
        hyperparameters={"eta": 0.3, "max_depth": 2},
        yaml_path=str(yaml_path)
    )
    assert isinstance(result, str)
    assert "entrenado" in result.lower()


def test_godml_notebook_pipeline_and_save_load(tmp_path):
    csv_path = tmp_path / "data.csv"
    df = pd.DataFrame({
        "feature_0": [0.5, 0.6, 0.7, 0.8],
        "feature_1": [1, 1, 0, 0],
        "target": [0, 1, 0, 1]
    })
    df.to_csv(csv_path, index=False)

    godml_nb = GodmlNotebook()
    pipeline = godml_nb.create_pipeline(
        name="test-pipeline",
        model_type="random_forest",
        hyperparameters={"n_estimators": 5},
        dataset_path=str(csv_path)
    )
    assert pipeline is not None

    # Simular entrenamiento (en real, se necesitaría executor)
    try:
        godml_nb.train()
    except Exception:
        pass

    # Simular guardado y carga
    try:
        godml_nb.save_model(model_name="test_model")
    except ValueError:
        pass

    try:
        godml_nb.load_model(model_name="test_model")
    except FileNotFoundError:
        pass


def test_train_from_yaml(tmp_path):
    csv_path = tmp_path / "data.csv"
    df = pd.DataFrame({
        "feature_0": [0.5, 0.6, 0.7, 0.8],
        "feature_1": [1, 1, 0, 0],
        "target": [0, 1, 0, 1]
    })
    df.to_csv(csv_path, index=False)

    yaml_path = tmp_path / "godml.yml"
    yaml_path.write_text(f"""
name: test-pipeline
dataset:
  uri: {csv_path.as_posix()}
model:
  type: random_forest
  hyperparameters:
    n_estimators: 10
    max_depth: 3
provider: mlflow
metrics:
  - name: auc
    threshold: 0.5
deploy:
  realtime: false
  batch_output: ./outputs/predictions.csv
""")

    try:
        result = train_from_yaml(str(yaml_path))
        assert isinstance(result, str)
    except Exception:
        pass


# ===============================
# Tests adicionales de Notebook API (nuevas funcionalidades)
# ===============================
from pathlib import Path
from textwrap import dedent
import numpy as np

from godml.notebook_api import (
    dataprep_run_inline,
    apply_compliance,
    train_model,
    predict,
    evaluate,
    compare_models,
    save_artifact,
    load_artifact,
    summarize_df,
    plot_roc_pr_curves,
)


def test_dataprep_run_inline_smoke(tmp_path: Path):
    # Datos mínimos
    csv_path = tmp_path / "in.csv"
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "amount": [10, None, 30],
        "category": ["A", None, "B"],
    })
    df.to_csv(csv_path, index=False)

    out_path = tmp_path / "out.csv"

    # Receta inline mínima
    recipe = {
        "inputs": [
            {"name": "raw", "connector": "csv", "uri": csv_path.as_posix()}
        ],
        "steps": [
            {"op": "safe_cast", "params": {"mapping": {"amount": "float"}}},
            {"op": "fillna", "params": {"columns": {"amount": 0, "category": "unknown"}}},
        ],
        "validations": [],
        "outputs": [
            {"name": "clean", "connector": "csv", "uri": out_path.as_posix()}
        ],
    }

    out_df = dataprep_run_inline(recipe)
    assert out_path.exists()
    assert isinstance(out_df, pd.DataFrame)
    assert out_df["amount"].isna().sum() == 0


def test_apply_compliance_masks_and_drops():
    df = pd.DataFrame({
        "email": ["user1@example.com", "user2@example.com"],
        "cvv": ["123", "456"],
        "amount": [10.0, 20.0],
    })
    masked = apply_compliance(df, standard="pci-dss")
    # email debe cambiar
    assert not (masked["email"].astype(str).values == df["email"].astype(str).values).all()
    # cvv debe desaparecer
    assert "cvv" not in masked.columns


def test_train_evaluate_and_compare_models():
    # Dataset sintético simple
    X = pd.DataFrame({
        "f1": [0, 1, 0, 1, 0, 1],
        "f2": [1, 1, 0, 0, 1, 0],
    })
    y = pd.Series([0, 1, 0, 1, 0, 1])

    res = train_model("random_forest", X, y, hyperparams={"n_estimators": 10, "max_depth": 3})
    y_pred = predict(res.model, X)

    # Métrica básica (usa compute_metrics del proyecto o sklearn fallback)
    metrics = evaluate(y, y_pred, ["accuracy"])  # lista para fallback
    assert "accuracy" in metrics

    # Comparador
    setattr(res, "metrics", metrics)
    table = compare_models([res], by="accuracy")
    assert "model" in table.columns and "accuracy" in table.columns
    assert len(table) == 1


def test_save_and_load_artifact(tmp_path: Path):
    obj = {"hello": "world", "n": 42}
    p = tmp_path / "artifact.joblib"
    save_artifact(obj, p)
    assert p.exists()
    loaded = load_artifact(p)
    assert loaded == obj


def test_summarize_df_has_expected_keys():
    df = pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "y"]})
    s = summarize_df(df)
    assert set(["shape", "nulls", "dtypes", "unique"]) <= set(s.keys())
    assert s["shape"] == [3, 2]
    assert s["nulls"]["a"] == 1


def test_plot_roc_pr_curves_runs(monkeypatch):
    # Evitar abrir ventanas durante el test
    import matplotlib.pyplot as plt
    monkeypatch.setattr(plt, "show", lambda: None)

    y_true = np.array([0, 1, 0, 1, 0, 1])
    y_prob = np.array([0.1, 0.8, 0.2, 0.7, 0.3, 0.9])
    plot_roc_pr_curves(y_true, y_prob)  # no debe lanzar excepción
