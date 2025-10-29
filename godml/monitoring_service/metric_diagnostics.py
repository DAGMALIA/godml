# godml/monitoring_service/metric_diagnostics.py
# Copyright (c) 2025 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import numpy as np
import logging

logger = logging.getLogger(__name__)

def analyze_metric_issue(y_true, y_pred_or_proba):
    """
    Analiza automáticamente por qué una métrica no pudo calcularse,
    aplicable a cualquier modelo registrado en GODML.
    """
    try:
        # --- Validaciones comunes ---
        if y_pred_or_proba is None or len(y_pred_or_proba) == 0:
            return "El modelo no generó predicciones o probabilidades.", "NO_OUTPUT"

        if np.any(np.isnan(y_pred_or_proba)):
            return "Se detectaron valores NaN en las salidas del modelo.", "NAN_VALUES"

        # --- Clasificación de tipo de salida ---
        if isinstance(y_pred_or_proba, np.ndarray):
            if y_pred_or_proba.ndim == 1:
                return "La salida del modelo es unidimensional; probablemente se usó predict() en lugar de predict_proba().", "SHAPE_1D"
            
            elif y_pred_or_proba.ndim == 2:
                n_true_classes = len(np.unique(y_true))
                n_pred_classes = y_pred_or_proba.shape[1]

                if n_pred_classes < n_true_classes:
                    return (f"Faltan clases en las predicciones: "
                            f"{n_pred_classes} predichas vs {n_true_classes} reales."), "MISSING_CLASSES"
                elif n_pred_classes > n_true_classes:
                    return (f"El modelo devolvió más columnas de las esperadas: "
                            f"{n_pred_classes} vs {n_true_classes}. "
                            f"Posible error en la codificación de etiquetas."), "EXTRA_CLASSES"
                else:
                    return "Error desconocido en el cálculo de métricas.", "GENERIC"
            else:
                return "La matriz de probabilidades tiene más de 2 dimensiones, formato no soportado.", "SHAPE_INVALID"

        return "Tipo de salida no reconocido para diagnóstico automático.", "UNKNOWN_TYPE"

    except Exception as e:
        return f"Error interno en el analizador de métricas: {e}", "INTERNAL"


def explain_issue_and_action(reason, code):
    """
    Genera una recomendación automatizada basada en el código de error.
    """
    suggestions = {
        "NO_OUTPUT": "Verifica que el modelo ejecute predict_proba() o predict() correctamente.",
        "NAN_VALUES": "Limpia el dataset o revisa el flujo de preprocesamiento (posibles NaNs).",
        "SHAPE_1D": "Usa predict_proba() para clasificación o revisa el método de predicción.",
        "MISSING_CLASSES": "Amplía el tamaño del set de test o balancea las clases antes de evaluar.",
        "EXTRA_CLASSES": "Verifica el label encoder o el mapeo de clases.",
        "SHAPE_INVALID": "Asegura que las probabilidades tengan forma [n_samples, n_classes].",
        "GENERIC": "Revisar logs previos para obtener el error raíz.",
        "INTERNAL": "Error en el analizador; posible bug interno.",
    }

    suggestion = suggestions.get(code, "Sin sugerencia específica disponible.")
    return f"💡 Causa: {reason}\n🎯 Acción sugerida: {suggestion}"
