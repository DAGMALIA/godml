import os
import pandas as pd
from godml.notebook_api import quick_train, quick_train_yaml

def test_quick_train_runs_without_error(tmp_path):
    # Prepara datos sintéticos
    df = pd.DataFrame({
        "feature_0": [0.1, 0.2, 0.3, 0.4],
        "feature_1": [1, 0, 1, 0],
        "target": [0, 1, 0, 1]
    })

    # Guarda CSV temporal
    csv_path = tmp_path / "data.csv"
    df.to_csv(csv_path, index=False)

    # Ejecuta entrenamiento
    result = quick_train(
        model_type="random_forest",
        hyperparameters={"n_estimators": 10, "max_depth": 3},
        dataset_path=str(csv_path)
    )

    # ✅ Espera string como salida
    assert isinstance(result, str)
    assert "entrenado exitosamente" in result.lower()

def test_quick_train_yaml_runs_and_saves(tmp_path):
    # Crea un archivo godml.yml temporal
    yaml_path = tmp_path / "godml.yml"
    yaml_path.write_text("""
name: test-pipeline
version: "1.0.0"
provider: mlflow
dataset:
  uri: ./test/data/churn.csv
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
  tags: [{source: test}]
deploy:
  realtime: false
  batch_output: ./outputs/predictions.csv
""")

    # Crea CSV
    df = pd.DataFrame({
        "feature_0": [1.0, 2.0, 3.0],
        "feature_1": [0, 1, 1],
        "target": [1, 0, 1]
    })
    (tmp_path / "data.csv").write_text(df.to_csv(index=False))

    # Ejecuta quick_train_yaml
    result = quick_train_yaml(
        model_type="xgboost",
        hyperparameters={"eta": 0.3, "max_depth": 2},
        yaml_path=str(yaml_path)
    )

    # ✅ Espera string como salida
    assert isinstance(result, str)
    assert "entrenado" in result.lower()
