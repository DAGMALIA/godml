# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import numpy as np
import pandas as pd
from typing import Any, Dict, Tuple
from keras.models import Sequential
from keras.layers import LSTM, Dense, Input
from keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from godml.monitoring_service.metrics import evaluate_regression
from godml.model_service.base_model_interface import BaseRegressionModel


class LSTMForecastModel(BaseRegressionModel):
    def __init__(self):
        self.model = None
        self.scaler = MinMaxScaler()
        self.look_back = 5

    def create_dataset(self, series: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X, y = [], []
        for i in range(len(series) - self.look_back):
            X.append(series[i:(i + self.look_back)])
            y.append(series[i + self.look_back])
        return np.array(X), np.array(y)

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        params: Dict
    ) -> Tuple[Any, np.ndarray, Dict[str, float]]:

        # Escalar
        series = X_train.squeeze()
        scaled_series = self.scaler.fit_transform(series.reshape(-1, 1)).flatten()

        X_seq, y_seq = self.create_dataset(scaled_series)
        X_seq = X_seq.reshape((X_seq.shape[0], X_seq.shape[1], 1))

        self.model = Sequential()
        self.model.add(Input(shape=(self.look_back, 1)))
        self.model.add(LSTM(params.get("units", 50)))
        self.model.add(Dense(1))
        self.model.compile(optimizer=Adam(learning_rate=params.get("learning_rate", 0.001)), loss="mse")

        self.model.fit(X_seq, y_seq, epochs=params.get("epochs", 20), batch_size=16, verbose=0)

        # Inference on test
        test_series = X_test.squeeze()
        scaled_test = self.scaler.transform(test_series.reshape(-1, 1)).flatten()
        X_test_seq, y_test_seq = self.create_dataset(scaled_test)
        X_test_scaled = self.scaler.transform(X_test.reshape(-1, 1)).reshape(X_test.shape[0], X_test.shape[1], 1)
        
        y_pred = self.model.predict(X_test_scaled, verbose=0)
        metrics = evaluate_regression(y_test, y_pred.flatten(), metric_names=params.get("metrics"))

        return self.model, y_pred.flatten(), metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        scaled_input = self.scaler.transform(X.values.reshape(-1, 1)).flatten()
        X_seq, _ = self.create_dataset(scaled_input)
        X_seq = X_seq.reshape((X_seq.shape[0], X_seq.shape[1], 1))
        return self.model.predict(X_seq, verbose=0).flatten()
