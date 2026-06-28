# godml/model_service/model_registry/xgboost_model.py
# Copyright (c) 2025 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import numpy as np
import pandas as pd
from typing import Dict, Tuple
import logging

try:
    from xgboost import XGBClassifier
except Exception as e:
    raise ImportError("Instala xgboost: pip install xgboost") from e

from sklearn.base import ClassifierMixin
from godml.model_service.base_model_interface import BaseClassificationModel
from godml.monitoring_service.metrics import evaluate_binary_classification

logger = logging.getLogger(__name__)


class XgboostModel(BaseClassificationModel):
    """
    Wrapper XGBoost alineado a la interfaz GODML (train/predict).
    Compatible con clasificación binaria, multiclase y regresión.
    """

    ALLOWED_PARAMS = {
        "n_estimators", "max_depth", "learning_rate", "eta", "subsample",
        "colsample_bytree", "gamma", "reg_alpha", "reg_lambda",
        "min_child_weight", "n_jobs", "random_state", "tree_method",
        "max_bin", "scale_pos_weight", "eval_metric", "verbosity",
        "objective", "num_class"
    }

    DEFAULTS = {
        "random_state": 42,
        "n_estimators": 200,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "logloss",
        "n_jobs": -1,
    }

    def __init__(self):
        self.model: XGBClassifier | None = None

    # ============================================================
    # 🧹 Limpieza y normalización de parámetros
    # ============================================================
    def _sanitize_params(self, params: Dict) -> Dict:
        """
        Limpia y normaliza parámetros incompatibles o inválidos antes de entrenar.
        """

        params = dict(params or {})

        # 🧠 Normaliza alias 'eta' → 'learning_rate'
        if "eta" in params and "learning_rate" not in params:
            params["learning_rate"] = params.pop("eta")

        # ⚠️ Limpieza de multi_class inválidos
        if "multi_class" in params:
            val = params["multi_class"]
            if val not in ("ovr", "ovo"):
                logger.warning(f"⚠️ Eliminando multi_class inválido '{val}' para XGBoost.")
                params.pop("multi_class", None)

        # ⚙️ Construcción segura del conjunto final
        full = self.DEFAULTS.copy()
        for k, v in params.items():
            full[k] = v  # prioriza los parámetros ajustados dinámicamente

        # 🔍 Log extendido para trazabilidad
        logger.debug(f"🧩 Parámetros combinados (DEFAULTS + custom): {full}")

        return full

    # ============================================================
    # 🚀 Entrenamiento del modelo
    # ============================================================
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        params: Dict
    ) -> Tuple[ClassifierMixin, np.ndarray, Dict[str, float]]:
        """
        Entrena el modelo XGBoost con limpieza automática y soporte multiclase.
        """

        full = self._sanitize_params(params)

        # Validación de coherencia entre objetivo y número de clases
        unique_classes = len(np.unique(y_train))
        if "num_class" in full and unique_classes > 2:
            full["objective"] = "multi:softprob"
            full["num_class"] = unique_classes
            logger.info(f"🧩 Ajuste automático multiclase detectado: num_class={unique_classes}, objective=multi:softprob")

        elif unique_classes == 2 and "objective" not in full:
            full["objective"] = "binary:logistic"
            logger.info("🧩 Ajuste automático binario detectado: objective=binary:logistic")

        elif unique_classes == 1:
            raise ValueError("❌ Dataset con una sola clase. No puede entrenarse un modelo supervisado.")

        logger.info(f"🚀 Entrenando XGBoost con hiperparámetros finales:\n{full}")

        # Inicialización robusta del modelo
        try:
            self.model = XGBClassifier(**full)
        except TypeError as e:
            logger.error(f"❌ Error creando XGBClassifier con params={full}")
            raise ValueError(f"Error al inicializar XGBoost: {e}")

        # Entrenamiento
        self.model.fit(X_train, y_train)

        # Predicción segura
        preds = self.model.predict_proba(X_test)
        if preds.shape[1] > 1:
            preds = preds[:, 1]  # binario o multiclass reducido

        # Evaluación métrica binaria (para mantener compatibilidad GODML)
        metrics = evaluate_binary_classification(y_test, preds)

        logger.info(f"✅ Entrenamiento XGBoost completado. Métricas: {metrics}")
        return self.model, preds, metrics

    # ============================================================
    # 🔮 Inferencia
    # ============================================================
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError("❌ El modelo no ha sido entrenado.")
        preds = self.model.predict_proba(X)
        if preds.shape[1] > 1:
            return preds[:, 1]
        return preds
