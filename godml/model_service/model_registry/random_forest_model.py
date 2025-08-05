# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import numpy as np
import pandas as pd
from typing import Dict, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import ClassifierMixin

from model_service.base_model_interface import BaseClassificationModel
from monitoring_service.metrics import evaluate_binary_classification


class RandomForestModel(BaseClassificationModel):
    """
    Implementación de modelo Random Forest para clasificación.
    Compatible con la arquitectura GODML.
    """

    ALLOWED_PARAMS = {
        'n_estimators', 'criterion', 'max_depth', 'min_samples_split', 'min_samples_leaf',
        'min_weight_fraction_leaf', 'max_features', 'max_leaf_nodes', 'min_impurity_decrease',
        'bootstrap', 'oob_score', 'n_jobs', 'random_state', 'verbose', 'warm_start',
        'class_weight', 'ccp_alpha', 'max_samples'
    }

    DEFAULTS = {
        'random_state': 42,
        'min_samples_leaf': 1,
        'max_features': 'sqrt'
    }

    def __init__(self):
        self.model: RandomForestClassifier = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        params: Dict
    ) -> Tuple[ClassifierMixin, np.ndarray, Dict[str, float]]:
        """
        Entrena un RandomForestClassifier y devuelve el modelo, predicciones y métricas.
        """

        # Forzar hiperparámetros requeridos por SonarQube
        for key, value in self.DEFAULTS.items():
            params.setdefault(key, value)

        valid_params = {k: v for k, v in params.items() if k in self.ALLOWED_PARAMS}
        self.model = RandomForestClassifier(**valid_params)
        self.model.fit(X_train, y_train)

        preds = self.model.predict_proba(X_test)[:, 1]
        metrics = evaluate_binary_classification(y_test, preds)

        return self.model, preds, metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Realiza predicciones sobre un conjunto de datos.
        """
        if self.model is None:
            raise ValueError("❌ El modelo no ha sido entrenado.")
        return self.model.predict_proba(X)[:, 1]
