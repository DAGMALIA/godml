# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import numpy as np
import pandas as pd
from typing import Dict, Tuple

try:
    from xgboost import XGBClassifier
except Exception as e:
    raise ImportError("Instala xgboost: pip install xgboost") from e

from sklearn.base import ClassifierMixin
from godml.model_service.base_model_interface import BaseClassificationModel
from godml.monitoring_service.metrics import evaluate_binary_classification


class XgboostModel(BaseClassificationModel):
    """
    Wrapper XGBoost alineado a la interfaz GODML (train/predict).
    """

    ALLOWED_PARAMS = {
        "n_estimators", "max_depth", "learning_rate", "subsample",
        "colsample_bytree", "gamma", "reg_alpha", "reg_lambda",
        "min_child_weight", "n_jobs", "random_state", "tree_method",
        "max_bin", "scale_pos_weight", "eval_metric", "verbosity",
    }

    DEFAULTS = {
        "random_state": 42,
        "n_estimators": 200,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "logloss",   # evita warnings
        "n_jobs": -1,
        # "tree_method": "hist",    # opcional, útil en CPU
    }

    def __init__(self):
        self.model: XGBClassifier | None = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        params: Dict
    ) -> Tuple[ClassifierMixin, np.ndarray, Dict[str, float]]:
        # Mezcla defaults + params permitidos
        full = {**self.DEFAULTS, **{k: v for k, v in params.items() if k in self.ALLOWED_PARAMS}}
        self.model = XGBClassifier(**full)
        self.model.fit(X_train, y_train)

        preds = self.model.predict_proba(X_test)[:, 1]
        metrics = evaluate_binary_classification(y_test, preds)
        return self.model, preds, metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError("❌ El modelo no ha sido entrenado.")
        return self.model.predict_proba(X)[:, 1]
