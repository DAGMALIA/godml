# tests/test_logistic_regression_model_cv.py

from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel
from godml.utils.cross_validation import evaluate_with_cv
from sklearn.datasets import load_breast_cancer
import pandas as pd

def test_evaluate_with_cv_logistic():
    data = load_breast_cancer()
    X = pd.DataFrame(data.data, columns=data.feature_names)
    y = data.target

    avg, all_folds = evaluate_with_cv(
        LogisticRegressionModel,
        X,
        y,
        task_type="classification",
        params={"max_iter": 500}
    )

    assert "accuracy" in avg
    assert avg["accuracy"] > 0.85
