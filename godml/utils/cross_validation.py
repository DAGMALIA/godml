# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from typing import Type, Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, KFold
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score
from godml.model_service.base_model_interface import BaseModel


def evaluate_with_cv(
    model_class: Type[BaseModel],
    X: pd.DataFrame,
    y: np.ndarray,
    task_type: str,
    params: Dict[str, Any],
    folds: int = 5,
    random_state: int = 42
) -> Tuple[Dict[str, float], List[Dict[str, float]]]:
    """
    Evalúa un modelo con validación cruzada estratificada o normal.

    Returns:
        - métricas promedio
        - métricas por fold
    """
    fold_metrics = []
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=random_state) if task_type == "classification" else KFold(n_splits=folds, shuffle=True, random_state=random_state)

    for train_idx, test_idx in splitter.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model = model_class()
        _, y_pred, metrics = model.train(X_train, y_train, X_test, y_test, params)
        fold_metrics.append(metrics)

    # Calcular métricas promedio
    avg_metrics = {
        metric: np.mean([m[metric] for m in fold_metrics])
        for metric in fold_metrics[0]
    }

    return avg_metrics, fold_metrics
