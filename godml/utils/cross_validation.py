# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from typing import Type, Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, KFold
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score
from godml.model_service.base_model_interface import BaseModel


def evaluate_with_cv(
    model_class_or_instance,
    X,
    y,
    task_type,
    params,
    folds: int = 5,
    random_state: int = 42
):
    fold_metrics = []
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=random_state) \
        if task_type == "classification" else \
        KFold(n_splits=folds, shuffle=True, random_state=random_state)

    for train_idx, test_idx in splitter.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # ✅ soportar clase o instancia
        model = model_class_or_instance() if isinstance(model_class_or_instance, type) else model_class_or_instance
        _, y_pred, metrics = model.train(X_train, y_train, X_test, y_test, params)
        fold_metrics.append(metrics)

    avg_metrics = {
        metric: np.mean([m[metric] for m in fold_metrics])
        for metric in fold_metrics[0]
    }

    return avg_metrics, fold_metrics

