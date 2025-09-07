import numpy as np
import pandas as pd
from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel

def test_logistic_regression_training_and_prediction():
    X_train = pd.DataFrame({
        'feature1': [0.1, 0.3, 0.5, 0.7, 0.9],
        'feature2': [1.2, 0.9, 1.5, 1.8, 2.0]
    })
    y_train = np.array([0, 0, 1, 1, 1])

    X_test = pd.DataFrame({
        'feature1': [0.2, 0.4],
        'feature2': [1.1, 1.4]
    })
    y_test = np.array([0, 1])

    params = {"C": 1.0, "solver": "liblinear", "max_iter": 100}
    model = LogisticRegressionModel()
    model_instance, predictions, metrics = model.train(X_train, y_train, X_test, y_test, params)

    # Asegura que la predicción tenga el mismo largo que y_test
    assert len(predictions) == len(y_test)
    assert isinstance(metrics, dict)
    assert "accuracy" in metrics

    new_preds = model.predict(X_test)
    assert len(new_preds) == len(X_test)