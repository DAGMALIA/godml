from godml.model_service.base_model_interface import BaseClassificationModel
from sklearn.linear_model import LogisticRegression
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Any


class LogisticRegressionModel(BaseClassificationModel):
    def __init__(self):
        self.model = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        params: Dict
    ) -> Tuple[Any, np.ndarray, Dict[str, float]]:
        self.model = LogisticRegression(**params)
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)
        metrics = {
            "accuracy": (y_pred == y_test).mean()
        }
        return self.model, y_pred, metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X)

