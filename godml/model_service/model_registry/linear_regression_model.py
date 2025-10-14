# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from godml.model_service.base_model_interface import BaseRegressionModel
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd


class LinearRegressionModel(BaseRegressionModel):
    def __init__(self):
        self.model = LinearRegression()

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        params: Dict
    ) -> Tuple[Any, np.ndarray, Dict[str, float]]:
        self.model.set_params(**params)
        self.model.fit(X_train, y_train)
        predictions = self.model.predict(X_test)

        metrics = {
            "mse": mean_squared_error(y_test, predictions),
            "r2": r2_score(y_test, predictions),
        }
        return self.model, predictions, metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X)
