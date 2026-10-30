# test_log_model_types.py
"""
Found by the README test (F1-14): with recent MLflow (skops serialization),
logging a RandomForest failed with "Untrusted types found:
['sklearn.tree._tree.Tree']" because godml only trusted XGBoost's types.
"""

import mlflow
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from godml.train.log_model_generic import log_model_generic

X = pd.DataFrame({"a": [0, 1, 2, 3, 4, 5, 6, 7], "b": [7, 6, 5, 4, 3, 2, 1, 0]})
y = [0, 0, 0, 0, 1, 1, 1, 1]


@pytest.mark.parametrize(
    "model",
    [
        RandomForestClassifier(n_estimators=3, random_state=0),
        LogisticRegression(),
        XGBClassifier(n_estimators=3),
    ],
    ids=["random_forest", "logistic_regression", "xgb_classifier"],
)
def test_sklearn_api_models_can_be_logged(tmp_path, monkeypatch, model):
    monkeypatch.chdir(tmp_path)
    mlflow.set_tracking_uri(f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}")
    mlflow.set_experiment("log-model-types")
    model.fit(X, y)
    with mlflow.start_run():
        log_model_generic(model, model_name="model", input_example=X.head(2))
