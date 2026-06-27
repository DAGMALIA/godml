import pytest
import numpy as np
import pandas as pd
import yaml


@pytest.fixture
def binary_dataset():
    np.random.seed(42)
    n = 120
    X = pd.DataFrame({
        "feat_a": np.random.randn(n),
        "feat_b": np.random.randn(n),
        "feat_c": np.random.randint(0, 10, n).astype(float),
    })
    y = np.where(X["feat_a"] + X["feat_b"] > 0, 1, 0)
    split = int(n * 0.8)
    return {
        "X_train": X.iloc[:split].reset_index(drop=True),
        "y_train": y[:split],
        "X_test": X.iloc[split:].reset_index(drop=True),
        "y_test": y[split:],
        "X": X,
        "y": y,
    }


@pytest.fixture
def regression_dataset():
    np.random.seed(42)
    n = 80
    X = pd.DataFrame({
        "x1": np.random.randn(n),
        "x2": np.random.randn(n),
    })
    y = 3.0 * X["x1"] + 2.0 * X["x2"] + np.random.randn(n) * 0.1
    split = int(n * 0.8)
    return {
        "X_train": X.iloc[:split].reset_index(drop=True),
        "y_train": y.values[:split],
        "X_test": X.iloc[split:].reset_index(drop=True),
        "y_test": y.values[split:],
    }


@pytest.fixture
def pii_dataframe():
    return pd.DataFrame({
        "card_number": ["4111111111111111", "5500005555555559", "340000000000009"],
        "email": ["user@example.com", "admin@test.org", "john@company.co"],
        "ssn": ["123-45-6789", "987-65-4321", "456-78-9012"],
        "zip_code": ["12345", "90210", "10001"],
        "age": [25, 30, 45],
        "score": [0.8, 0.6, 0.9],
    })


@pytest.fixture
def minimal_pipeline_config():
    return {
        "name": "test-pipeline",
        "version": "1.0.0",
        "provider": "mlflow",
        "dataset": {
            "uri": "./data/test.csv",
            "hash": "auto",
        },
        "model": {
            "type": "xgboost",
            "hyperparameters": {"max_depth": 3},
        },
        "metrics": [{"name": "auc", "threshold": 0.7}],
        "governance": {
            "owner": "test@company.com",
        },
        "deploy": {
            "realtime": False,
            "batch_output": "./outputs/preds.csv",
        },
    }


@pytest.fixture
def temp_yaml(tmp_path, minimal_pipeline_config):
    f = tmp_path / "godml.yml"
    f.write_text(yaml.dump(minimal_pipeline_config))
    return str(f)
