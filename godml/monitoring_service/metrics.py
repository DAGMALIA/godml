# godml/monitoring_service/metrics.py
# Copyright (c) 2025 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License
from godml.monitoring_service.metric_diagnostics import analyze_metric_issue, explain_issue_and_action
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    mean_squared_error, 
    mean_absolute_error, 
    r2_score,
    log_loss
)
import numpy as np
import logging

logger = logging.getLogger(__name__)

def evaluate_binary_classification(y_true, y_proba, threshold=0.5):
    """
    Evalúa un modelo de clasificación binaria o multiclase.
    Compatible con XGBoost, RandomForest, LogisticRegression y LSTMForecast.
    """
    y_true = np.array(y_true)
    y_proba = np.array(y_proba)

    # Detectar multiclase
    n_classes = len(np.unique(y_true))
    is_multiclass = n_classes > 2

    try:
        if is_multiclass:
            logger.info(f"🧩 Evaluando multiclase ({n_classes} clases)")

            # Convertir probabilidades a etiquetas (argmax)
            if y_proba.ndim > 1:
                y_pred_labels = np.argmax(y_proba, axis=1)
            else:
                # fallback raro, pero defensivo
                y_pred_labels = y_proba.round().astype(int)

            metrics = {}

            # Métricas basadas en etiquetas
            metrics["accuracy"] = accuracy_score(y_true, y_pred_labels)
            metrics["f1_macro"] = f1_score(y_true, y_pred_labels, average="macro", zero_division=0)

            # Asegurar que las clases estén completas
            unique_labels = np.unique(y_true)

            # Métricas basadas en probabilidades
            try:
                # Si el número de columnas de y_proba no coincide con las clases reales,
                # ajustamos dinámicamente las etiquetas esperadas.
                if y_proba.ndim > 1 and y_proba.shape[1] != len(unique_labels):
                    logger.warning(
                        f"⚠️ Ajustando labels para evaluación: {len(unique_labels)} clases en y_true vs {y_proba.shape[1]} en y_proba"
                    )
                    unique_labels = np.arange(y_proba.shape[1])

                metrics["log_loss"] = log_loss(y_true, y_proba, labels=unique_labels)
                metrics["roc_auc_ovr"] = roc_auc_score(
                    y_true, y_proba, multi_class="ovr", average="macro", labels=unique_labels
                )
            except Exception as prob_err:
                reason, code = analyze_metric_issue(y_true, y_proba)
                logger.warning(f"⚠️ AUC no calculada ({code}): {reason}")
                logger.info(explain_issue_and_action(reason, code))
                metrics["auc"] = np.nan


            return metrics

        else:
            logger.info("🧩 Evaluando binaria")

            y_pred_binary = (y_proba > threshold).astype(int)
            return {
                "auc": roc_auc_score(y_true, y_proba),
                "accuracy": accuracy_score(y_true, y_pred_binary),
                "precision": precision_score(y_true, y_pred_binary, zero_division=0),
                "recall": recall_score(y_true, y_pred_binary, zero_division=0),
                "f1": f1_score(y_true, y_pred_binary, zero_division=0),
            }

    except Exception as e:
        logger.warning(f"⚠️ Error calculando métricas: {e}")
        return {"error": str(e)}


def evaluate_regression(y_true, y_pred, metric_names=None):
    """
    Evalúa métricas de regresión dinámicamente.
    """
    available_metrics = {
        "mse": mean_squared_error,
        "mae": mean_absolute_error,
        "r2": r2_score
    }

    if not metric_names:
        metric_names = list(available_metrics.keys())

    results = {}
    for name in metric_names:
        func = available_metrics.get(name)
        if func:
            try:
                results[name] = func(y_true, y_pred)
            except Exception as e:
                logger.warning(f"⚠️ Error calculando {name}: {e}")
    return results
