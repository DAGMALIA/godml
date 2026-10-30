# test_serving_features.py
"""
F1-11: the inference servers built the DataFrame in the order the client sent
the JSON keys. sklearn models reject a different column order and an XGBoost
Booster (DMatrix) uses position, so the same payload with reordered keys
failed or mispredicted. Probabilities were never returned.
"""

import importlib

import numpy as np
import pandas as pd
import pytest
import xgboost as xgb
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression

SERVERS = ["godml.serve.deploy.server", "godml.templates.deploy_template.server"]

TRAIN = pd.DataFrame(
    {"a": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0], "b": [5.0, 3.0, 4.0, 1.0, 2.0, 0.0]}
)
LABEL = [0, 0, 0, 1, 1, 1]
ROW = {"a": 4.5, "b": 0.5}
REORDERED = {"b": 0.5, "a": 4.5}


@pytest.fixture(params=SERVERS)
def client(request):
    module = importlib.import_module(request.param)
    saved = getattr(module.app.state, "model", None)

    def with_model(model):
        module.app.state.model = model
        return TestClient(module.app)

    yield with_model
    module.app.state.model = saved


@pytest.fixture
def sklearn_model():
    return LogisticRegression().fit(TRAIN, LABEL)


@pytest.fixture
def booster():
    dtrain = xgb.DMatrix(TRAIN, label=LABEL)
    return xgb.train({"objective": "binary:logistic"}, dtrain, num_boost_round=5)


def test_sklearn_reordered_keys_give_same_prediction(client, sklearn_model):
    api = client(sklearn_model)
    expected = sklearn_model.predict(pd.DataFrame([ROW]))[0]
    response = api.post("/predict", json={"data": REORDERED})
    assert response.status_code == 200, response.text
    assert response.json()["prediction"] == [expected]


def test_sklearn_returns_probabilities(client, sklearn_model):
    body = client(sklearn_model).post("/predict", json={"data": ROW}).json()
    proba = body["probabilities"]
    assert len(proba) == 1 and len(proba[0]) == 2
    assert np.isclose(sum(proba[0]), 1.0)


def test_booster_reordered_keys_give_same_prediction(client, booster):
    expected = booster.predict(xgb.DMatrix(pd.DataFrame([ROW])))[0]
    response = client(booster).post("/predict", json={"data": REORDERED})
    assert response.status_code == 200, response.text
    assert response.json()["prediction"] == pytest.approx([expected])


def test_missing_feature_is_a_client_error(client, sklearn_model):
    response = client(sklearn_model).post("/predict", json={"data": {"a": 1.0}})
    assert response.status_code == 400
    assert "b" in response.text


def test_extra_keys_are_ignored(client, sklearn_model):
    response = client(sklearn_model).post(
        "/predict", json={"data": {**ROW, "unused": 1}}
    )
    assert response.status_code == 200, response.text
