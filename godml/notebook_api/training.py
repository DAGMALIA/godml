from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from ._core import _fit_any, _predict_any, _get_model


def train_model(
    model_type: str,
    X: pd.DataFrame,
    y: pd.Series,
    hyperparams: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
):
    model = _get_model(model_type, **(hyperparams or {}))
    if seed is not None and hasattr(model, "set_random_state"):
        try:
            model.set_random_state(seed)
        except Exception:
            pass
    if hyperparams and hasattr(model, "set_hyperparameters"):
        try:
            model.set_hyperparameters(hyperparams)
        except Exception:
            pass
    _fit_any(model, X, y, hyperparams or {})
    return type("ModelResultLike", (), {"model": model, "metrics": None})()


def predict(model_or_wrapper: Any, X: pd.DataFrame):
    model = getattr(model_or_wrapper, "model", model_or_wrapper)
    return _predict_any(model, X)


def evaluate(y_true, y_pred, metrics: Sequence[str] | Dict[str, Any]) -> Dict[str, float]:
    try:
        from godml.monitoring_service.metrics import compute_metrics as _cm
        return _cm(y_true, y_pred, metrics)
    except Exception:
        pass
    try:
        from sklearn import metrics as sk
    except Exception as e:
        raise ImportError("Se requiere scikit-learn para evaluate().") from e

    wanted = list(metrics.keys()) if isinstance(metrics, dict) else list(metrics)
    out: Dict[str, float] = {}
    y_pred_arr = np.asarray(y_pred)
    is_prob_like = y_pred_arr.dtype.kind in {"f"} and y_pred_arr.min() >= 0 and y_pred_arr.max() <= 1

    for m in wanted:
        m_l = m.lower()
        if m_l in {"accuracy", "acc"}:
            out[m] = float(sk.accuracy_score(y_true, (y_pred_arr > 0.5) if is_prob_like else y_pred_arr))
        elif m_l in {"precision", "prec"}:
            out[m] = float(sk.precision_score(y_true, (y_pred_arr > 0.5) if is_prob_like else y_pred_arr))
        elif m_l in {"recall", "tpr"}:
            out[m] = float(sk.recall_score(y_true, (y_pred_arr > 0.5) if is_prob_like else y_pred_arr))
        elif m_l in {"f1", "f1_score"}:
            out[m] = float(sk.f1_score(y_true, (y_pred_arr > 0.5) if is_prob_like else y_pred_arr))
        elif m_l in {"roc_auc", "auc"} and is_prob_like:
            out[m] = float(sk.roc_auc_score(y_true, y_pred_arr))
        else:
            func = getattr(sk, f"{m_l}_score", None)
            if callable(func):
                out[m] = float(func(y_true, y_pred_arr))
    return out


def compare_models(results: Iterable[Any], by: str = "roc_auc") -> pd.DataFrame:
    rows = []
    for r in results:
        metrics = getattr(r, "metrics", None) or {}
        rows.append({"model": type(getattr(r, "model", r)).__name__, **metrics})
    df = pd.DataFrame(rows)
    if by in df.columns:
        df = df.sort_values(by=by, ascending=False)
    return df.reset_index(drop=True)
