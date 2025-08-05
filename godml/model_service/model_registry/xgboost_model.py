# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from typing import Dict, Tuple
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.base import ClassifierMixin 

from model_service.base_model_interface import BaseClassificationModel
from monitoring_service.metrics import evaluate_binary_classification


class XgboostModel(BaseClassificationModel):
    """
    Implementación del modelo XGBoost para clasificación binaria.
    """

    def __init__(self):
        self.model = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        params: Dict
    ) -> Tuple[xgb.Booster, np.ndarray, Dict[str, float]]:
        """
        Entrena el modelo XGBoost con los datos proporcionados.
        """
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dtest = xgb.DMatrix(X_test, label=y_test)

        self.model = xgb.train(params, dtrain, num_boost_round=params.get("num_boost_round", 100))
        preds = self.model.predict(dtest)

        metrics = evaluate_binary_classification(y_test, preds)

        return self.model, preds, metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Realiza predicciones con el modelo entrenado.
        """
        if self.model is None:
            raise ValueError("❌ El modelo XGBoost no ha sido entrenado.")
        
        dmatrix = xgb.DMatrix(X)
        return self.model.predict(dmatrix)

