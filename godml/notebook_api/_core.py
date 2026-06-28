"""Internal helpers shared across notebook_api submodules."""
from __future__ import annotations

import importlib
from typing import Any, Dict


_DEF_REGISTRY: Dict[str, str] = {
    "random_forest": "godml.model_service.model_registry.random_forest_model:RandomForestModel",
    "rf": "godml.model_service.model_registry.random_forest_model:RandomForestModel",
    "xgboost": "godml.model_service.model_registry.xgboost_model:XgboostModel",
    "xgb": "godml.model_service.model_registry.xgboost_model:XgboostModel",
    "logistic_regression": "godml.model_service.model_registry.logistic_regression_model:LogisticRegressionModel",
    "logreg": "godml.model_service.model_registry.logistic_regression_model:LogisticRegressionModel",
}


def _import_symbol(path: str) -> Any:
    module_path, _, attr = path.partition(":")
    mod = importlib.import_module(module_path)
    return getattr(mod, attr)


def _fit_any(m, X, y, hyperparams: Dict[str, Any] | None = None):
    """Trains using whatever convention the wrapper exposes."""
    hyperparams = hyperparams or {}
    candidates = [m, getattr(m, "estimator", None), getattr(m, "clf", None), getattr(m, "model", None)]
    for cand in candidates:
        if cand is None:
            continue
        fit = getattr(cand, "fit", None)
        if callable(fit):
            try:
                fit(X, y)
                return
            except TypeError:
                pass
        train = getattr(cand, "train", None)
        if callable(train):
            for args in [(X, y), (X, y, {}), (X, y, None), (X, y, X, y), (X, y, X, y, {}), (X, y, X, y, hyperparams)]:
                try:
                    train(*args)
                    return
                except TypeError:
                    continue
    try:
        for v in vars(m).values():
            fit = getattr(v, "fit", None)
            if callable(fit):
                try:
                    fit(X, y)
                    return
                except TypeError:
                    continue
    except Exception:
        pass
    raise AttributeError("El modelo no expone 'fit', 'train' ni sub-atributos compatibles")


def _predict_any(m, X):
    """Prediction tolerant to wrapper conventions."""
    def _try_one(obj):
        if obj is None:
            return None
        if hasattr(obj, "predict_proba"):
            try:
                proba = obj.predict_proba(X)
                if isinstance(proba, (list, tuple)):
                    proba = proba[1]
                return proba[:, 1] if hasattr(proba, "ndim") and proba.ndim == 2 and proba.shape[1] > 1 else proba
            except Exception:
                pass
        if hasattr(obj, "predict"):
            return obj.predict(X)
        return None

    for cand in [m, getattr(m, "model", None), getattr(m, "estimator", None), getattr(m, "clf", None)]:
        out = _try_one(cand)
        if out is not None:
            return out
    try:
        for v in vars(m).values():
            out = _try_one(v)
            if out is not None:
                return out
    except Exception:
        pass
    raise AttributeError("No se encontró método de predicción compatible")


def _get_model(model_type: str, **hyperparams):
    key = (model_type or "").lower()
    if key not in _DEF_REGISTRY:
        raise ValueError(f"Modelo no soportado: {model_type}. Disponibles: {sorted(set(_DEF_REGISTRY))}")
    cls = _import_symbol(_DEF_REGISTRY[key])
    try:
        return cls(**(hyperparams or {}))
    except TypeError:
        model = cls()
        if hyperparams:
            if hasattr(model, "set_params") and callable(getattr(model, "set_params")):
                try:
                    model.set_params(**hyperparams)
                    return model
                except Exception:
                    pass
            for k, v in hyperparams.items():
                try:
                    setattr(model, k, v)
                except Exception:
                    pass
        return model
