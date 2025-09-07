from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    mean_squared_error, 
    mean_absolute_error, 
    r2_score
)

def evaluate_binary_classification(y_true, y_proba, threshold=0.5):
    """
    Evalúa un modelo de clasificación binaria.
    
    Args:
        y_true: Valores reales.
        y_proba: Probabilidades (output del modelo).
        threshold: Umbral para convertir probabilidades en clases (default 0.5).
    
    Returns:
        dict con métricas: auc, accuracy, precision, recall, f1
    """
    y_pred_binary = (y_proba > threshold).astype(int)
    
    return {
        "auc": roc_auc_score(y_true, y_proba),
        "accuracy": accuracy_score(y_true, y_pred_binary),
        "precision": precision_score(y_true, y_pred_binary, zero_division=0),
        "recall": recall_score(y_true, y_pred_binary, zero_division=0),
        "f1": f1_score(y_true, y_pred_binary, zero_division=0),
    }

def evaluate_regression(y_true, y_pred, metric_names=None):
    """
    Evalúa métricas de regresión dinámicamente.

    Args:
        y_true: Valores reales.
        y_pred: Predicciones del modelo.
        metric_names: Lista de nombres de métricas. Ejemplo: ["mse", "mae", "r2"]

    Returns:
        dict con las métricas solicitadas.
    """
    available_metrics = {
        "mse": mean_squared_error,
        "mae": mean_absolute_error,
        "r2": r2_score
    }

    # Si no se especifican métricas, usar todas
    if not metric_names:
        metric_names = list(available_metrics.keys())

    results = {}
    for name in metric_names:
        metric_func = available_metrics.get(name)
        if metric_func:
            results[name] = metric_func(y_true, y_pred)

    return results