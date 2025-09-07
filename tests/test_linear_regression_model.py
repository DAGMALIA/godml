import pandas as pd
import numpy as np
from godml.model_service.model_registry.linear_regression_model import LinearRegressionModel

def test_linear_regression_training_and_prediction():
    # Datos de prueba
    X = pd.DataFrame({
        "feature1": [1, 2, 3, 4, 5],
        "feature2": [10, 20, 30, 40, 50],
    })
    y = np.array([15, 30, 45, 60, 75])

    X_train, X_test = X.iloc[:4], X.iloc[4:]
    y_train, y_test = y[:4], y[4:]

    model = LinearRegressionModel()
    trained_model, predictions, metrics = model.train(X_train, y_train, X_test, y_test, params={})

    assert trained_model is not None
    assert isinstance(predictions, np.ndarray)
    assert "mse" in metrics
    assert "r2" in metrics

    y_pred = model.predict(X_test)
    assert y_pred.shape == y_test.shape
