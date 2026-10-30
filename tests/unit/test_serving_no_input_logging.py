# test_serving_no_input_logging.py
"""
F1-21: the scaffold server logged every request with
`godml_logger.info(str(df))`, so feature values (PII included) ended up in
the service logs. Only the shape and column names may be logged.
"""

import importlib
import logging

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression

SERVERS = ["godml.serve.deploy.server", "godml.templates.deploy_template.server"]
SENTINEL = 987654.321


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@pytest.fixture
def godml_logs():
    logger = logging.getLogger("GODML")
    handler, level = Capture(), logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler.messages
    logger.removeHandler(handler)
    logger.setLevel(level)


@pytest.mark.parametrize("module_name", SERVERS)
def test_request_values_are_not_logged(module_name, godml_logs):
    module = importlib.import_module(module_name)
    train = pd.DataFrame({"a": [0.0, 1.0, 2.0, 3.0], "b": [3.0, 2.0, 1.0, 0.0]})
    saved = getattr(module.app.state, "model", None)
    module.app.state.model = LogisticRegression().fit(train, [0, 0, 1, 1])
    try:
        response = TestClient(module.app).post(
            "/predict", json={"data": {"a": SENTINEL, "b": 1.5}}
        )
    finally:
        module.app.state.model = saved
    assert response.status_code == 200, response.text
    leaked = [m for m in godml_logs if str(SENTINEL) in m or "987654" in m]
    assert leaked == []


def test_template_logs_shape_and_columns(godml_logs):
    module = importlib.import_module("godml.templates.deploy_template.server")
    train = pd.DataFrame({"a": [0.0, 1.0, 2.0, 3.0], "b": [3.0, 2.0, 1.0, 0.0]})
    saved = getattr(module.app.state, "model", None)
    module.app.state.model = LogisticRegression().fit(train, [0, 0, 1, 1])
    try:
        TestClient(module.app).post("/predict", json={"data": {"a": 1.0, "b": 2.0}})
    finally:
        module.app.state.model = saved
    assert any("1x2" in m and "['a', 'b']" in m for m in godml_logs), godml_logs
