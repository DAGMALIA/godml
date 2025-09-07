# tests/test_base_regression_model.py

import numpy as np
import pandas as pd
from godml.model_service.base_model_interface import BaseRegressionModel
from dummy_regression_model import DummyRegressionModel

def test_regression_model_interface():
    model = DummyRegressionModel()
    X = pd.DataFrame({"feature": [1.0, 2.0, 3.0]})
    y = np.array([1.5, 2.5, 3.5])

    trained_model, predictions, metrics = model.train(X, y, X, y, {})
    
    assert isinstance(model, BaseRegressionModel)
    assert model.task_type == "regression"
    assert isinstance(predictions, np.ndarray)
    assert metrics == {"mse": 0.0}
