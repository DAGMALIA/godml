# tests/dummy_regression_model.py

from godml.model_service.base_model_interface import BaseRegressionModel
import numpy as np
import pandas as pd

class DummyRegressionModel(BaseRegressionModel):
    def train(self, X_train, y_train, X_test, y_test, params):
        return self, np.zeros(len(X_test)), {"mse": 0.0}

    def predict(self, X):
        return np.zeros(len(X))
