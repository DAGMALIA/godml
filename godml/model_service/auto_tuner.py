# godml/model_service/auto_tuner.py
# Copyright (c) 2025 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def auto_tune_hyperparameters(model_type: str, params: dict, X_train, y_train):
    """
    Ajusta automáticamente hiperparámetros críticos según el tipo de modelo y el dataset.
    Robustecido para distinguir correctamente entre clasificación binaria, multiclase y regresión.
    """

    model_type = model_type.lower()
    params = dict(params or {})

    # === 🧩 Detección robusta de tipo de problema ===
    if isinstance(y_train, (pd.Series, pd.DataFrame)):
        y_values = y_train.values.ravel()
    else:
        y_values = np.array(y_train).ravel()

    n_classes = len(np.unique(y_values))

    # Regla más tolerante a floats provenientes de label_encode
    is_classification = n_classes <= 20 and np.all(np.isfinite(y_values))
    is_multiclass = is_classification and n_classes > 2

    logger.info(f"🔍 Detección automática: n_classes={n_classes}, classification={is_classification}, multiclase={is_multiclass}")

    # === ⚙️ Ajustes automáticos por tipo de modelo ===
    if model_type == "xgboost":
        params.pop("multi_class", None)
        if is_multiclass:
            params.setdefault("objective", "multi:softprob")
            params.setdefault("num_class", int(n_classes))
            params.setdefault("eval_metric", "mlogloss")
            logger.info(f"🧠 Auto-tuning XGBoost: multiclase detectada ({n_classes} clases)")
        elif is_classification:
            params.setdefault("objective", "binary:logistic")
            params.setdefault("eval_metric", "auc")
            logger.info("🧠 Auto-tuning XGBoost: clasificación binaria detectada")
        else:
            params.setdefault("objective", "reg:squarederror")
            params.pop("num_class", None)
            logger.info("🧠 Auto-tuning XGBoost: regresión detectada")

    elif model_type == "random_forest":
        if is_multiclass:
            params.setdefault("criterion", "gini")
            logger.info(f"🧠 Auto-tuning RandomForest: multiclase ({n_classes} clases)")
        elif is_classification:
            params.setdefault("criterion", "entropy")
            logger.info("🧠 Auto-tuning RandomForest: binaria detectada")
        else:
            params.setdefault("criterion", "squared_error")
            logger.info("🧠 Auto-tuning RandomForest: regresión detectada")

    elif model_type == "logistic_regression":
        if is_multiclass:
            params.setdefault("multi_class", "ovr")
            params.setdefault("solver", "lbfgs")
            logger.info("🧠 Auto-tuning LogisticRegression: multiclase detectada")
        else:
            params.setdefault("solver", "liblinear")
            params.pop("multi_class", None)
            logger.info("🧠 Auto-tuning LogisticRegression: binaria detectada")

    elif model_type == "lstm_forecast":
        # Series temporales
        params.setdefault("sequence_length", min(len(X_train), 30))
        params.setdefault("epochs", 10)
        params.setdefault("batch_size", 16)
        logger.info(f"🧠 Auto-tuning LSTMForecast: seq_len={params['sequence_length']}, epochs={params['epochs']}")

    else:
        logger.info(f"ℹ️ Auto-tuning no definido para modelo: {model_type}")

    # === 🧹 Limpieza global final ===
    invalid_multi = params.get("multi_class")
    if invalid_multi and invalid_multi not in ("ovr", "ovo", "multinomial"):
        logger.warning(f"⚠️ Eliminando multi_class inválido '{invalid_multi}'")
        params.pop("multi_class", None)

    params = {k: v for k, v in params.items() if v is not None}

    logger.info(f"✅ Hiperparámetros finales para {model_type}: {params}")
    return params