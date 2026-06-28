from __future__ import annotations

import numpy as np


def suggest_search_space(model_type: str) -> dict:
    m = (model_type or "").lower()
    if m in {"random_forest", "rf"}:
        return {
            "n_estimators": [100, 200, 400, 800],
            "max_depth": [3, 4, 6, 8, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "max_features": ["sqrt", "log2", None],
            "bootstrap": [True, False],
        }
    if m in {"xgboost", "xgb"}:
        return {
            "n_estimators": [100, 200, 400, 800],
            "max_depth": [3, 4, 6, 8],
            "learning_rate": [0.03, 0.05, 0.1, 0.2],
            "subsample": [0.7, 0.8, 1.0],
            "colsample_bytree": [0.7, 0.8, 1.0],
            "reg_lambda": [0.0, 1.0, 3.0, 5.0],
        }
    if m in {"logistic_regression", "logreg", "logistic"}:
        return {
            "C": [0.01, 0.1, 1.0, 3.0, 10.0],
            "penalty": ["l2"],
            "solver": ["lbfgs"],
            "max_iter": [200, 400, 800],
        }
    return {}


def _sklearn_scoring(metric: str, y) -> str:
    m = (metric or "").lower().strip()
    if m == "roc_auc":
        return "roc_auc_ovr" if getattr(y, "nunique", lambda: 2)() > 2 else "roc_auc"
    return m


def _sk_estimator_for(model_type: str):
    key = (model_type or "").lower()
    if key in {"random_forest", "rf"}:
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier
    if key in {"logistic_regression", "logreg", "logistic"}:
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression
    if key in {"xgboost", "xgb"}:
        try:
            from xgboost import XGBClassifier
            return XGBClassifier
        except Exception as e:
            raise ImportError("xgboost no está instalado para usar XGBClassifier") from e
    raise ValueError(f"No hay mapeo sklearn para model_type='{model_type}'")


def tune_model(
    model_type: str,
    X,
    y,
    search_space: dict | None = None,
    metric: str = "roc_auc",
    cv: int = 5,
    max_trials: int = 30,
    time_budget_s: int | None = None,
    seed: int = 42,
    use_optuna: bool = False,
    n_jobs: int | None = None,
):
    if use_optuna:
        try:
            import optuna  # noqa: F401
        except Exception:
            print("Optuna no está instalado; continuo con RandomizedSearchCV.")
            use_optuna = False

    if use_optuna:
        raise NotImplementedError("Optuna backend no implementado aún.")

    try:
        from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, KFold
        import pandas as _pd
    except Exception as e:
        raise ImportError("Se requiere scikit-learn para tune_model().") from e

    EstCls = _sk_estimator_for(model_type)
    try:
        tmp = EstCls()
        est_params = tmp.get_params()
    except Exception:
        est_params = {}
    est_kwargs = {}
    if "random_state" in est_params:
        est_kwargs["random_state"] = seed
    estimator = EstCls(**est_kwargs)

    search_space = search_space or suggest_search_space(model_type)

    is_classif = getattr(y, "nunique", lambda: 2)() <= 20
    cv_split = (
        StratifiedKFold(n_splits=cv, shuffle=True, random_state=seed)
        if is_classif
        else KFold(n_splits=cv, shuffle=True, random_state=seed)
    )
    scoring = _sklearn_scoring(metric, y)

    rs = RandomizedSearchCV(
        estimator=estimator,
        param_distributions=search_space,
        n_iter=max_trials,
        scoring=scoring,
        cv=cv_split,
        random_state=seed,
        n_jobs=n_jobs if n_jobs is not None else (-1 if is_classif else None),
        verbose=0,
        refit=True,
    )
    rs.fit(X, y)

    return {
        "best_params": rs.best_params_,
        "best_score": float(rs.best_score_),
        "cv_results": _pd.DataFrame(rs.cv_results_),
        "best_estimator": rs.best_estimator_,
    }


def optimize_threshold(y_true, y_prob, metric: str = "f1"):
    try:
        from sklearn import metrics as sk
    except Exception as e:
        raise ImportError("Se requiere scikit-learn y numpy para optimize_threshold.") from e

    y_prob = np.asarray(y_prob).ravel()
    candidates = np.linspace(0.05, 0.95, 19)
    best_thr, best_score = 0.5, -1.0
    for thr in candidates:
        y_hat = (y_prob >= thr).astype(int)
        if metric == "f1":
            s = sk.f1_score(y_true, y_hat)
        elif metric == "precision":
            s = sk.precision_score(y_true, y_hat)
        elif metric == "recall":
            s = sk.recall_score(y_true, y_hat)
        else:
            s = sk.f1_score(y_true, y_hat)
        if s > best_score:
            best_thr, best_score = thr, s
    return float(best_thr), float(best_score)
