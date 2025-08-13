import pandas as pd
from godml import notebook_api as nb

def test_suggest_search_space_has_keys():
    rf = nb.suggest_search_space("random_forest")
    assert "n_estimators" in rf and "max_depth" in rf

def test_tune_model_rf_returns_best():
    # dataset simple binario
    X = pd.DataFrame({"x1": [0,1,0,1,0,1,0,1], "x2": [1,1,0,0,1,0,1,0]})
    y = pd.Series([0,1,0,1,0,1,0,1])

    space = {"n_estimators": [10, 20], "max_depth": [3, None]}
    out = nb.tune_model("random_forest", X, y, search_space=space, metric="roc_auc", cv=2, max_trials=2, seed=42)
    assert "best_params" in out and "best_score" in out and "best_estimator" in out

def test_optimize_threshold_improves_f1():
    y_true = pd.Series([0,0,1,1,1,0,1,0,1,0])
    y_prob = pd.Series([0.1,0.2,0.6,0.8,0.7,0.3,0.9,0.4,0.65,0.2])
    thr, f1 = nb.optimize_threshold(y_true, y_prob, metric="f1")
    assert 0.0 < thr < 1.0
    assert f1 > 0.0
