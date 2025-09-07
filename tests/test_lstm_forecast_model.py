import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from godml.model_service.model_registry.lstm_forecast_model import LSTMForecastModel


def test_lstm_forecast_training_and_prediction():
    # Datos sintéticos de ejemplo
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    values = np.sin(np.linspace(0, 20, 100)) + np.random.normal(0, 0.1, 100)
    df = pd.DataFrame({"ds": dates, "y": values})

    # Crear secuencias para LSTM
    look_back = 5
    X = []
    y = []
    for i in range(len(df) - look_back):
        X.append(df["y"].values[i:i + look_back])
        y.append(df["y"].values[i + look_back])
    X = np.array(X)
    y = np.array(y)

    # Separar train/test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Parámetros del modelo
    params = {
        "epochs": 2,
        "batch_size": 4,
        "look_back": look_back,
        "n_units": 32,
        "metrics": ["mse", "mae", "r2"]
    }

    # Entrenamiento
    model = LSTMForecastModel()
    trained_model, y_pred, metrics = model.train(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        params=params
    )

    # Validaciones
    assert trained_model is not None
    assert isinstance(y_pred, np.ndarray)
    assert y_pred.shape == y_test.shape

    # Validar que las métricas existan y sean tipo float
    for metric in params["metrics"]:
        assert metric in metrics, f"{metric} no fue calculada"
        assert isinstance(metrics[metric], float), f"{metric} no es float"
