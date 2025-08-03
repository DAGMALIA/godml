from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
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