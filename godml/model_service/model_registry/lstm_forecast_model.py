# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import numpy as np
import pandas as pd
from typing import Any, Dict, Tuple
from keras.models import Sequential
from keras.layers import LSTM, Dense, Input
from keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler
from godml.monitoring_service.metrics import evaluate_regression
from godml.model_service.base_model_interface import BaseRegressionModel


class LstmForecastModel(BaseRegressionModel):
    """
    GODML | v1.0.2-R4
    🎯 Versión gobernada: prioriza configuración YAML, con fallback inteligente solo ante errores.
    """

    def __init__(self):
        self.model = None
        self.scaler = MinMaxScaler()
        self.look_back = 5
        self.target_hint = None
        self._yaml_configured = False

    # --- CONFIGURACIÓN CONTROLADA ---
    def configure_from_yaml(self, params: Dict, dataset_target: str = None):
        """Configura el modelo según el YAML. Fallback si faltan valores."""
        try:
            self.look_back = int(params.get("look_back", self.look_back))
            self.target_hint = dataset_target or self.target_hint
            self._yaml_configured = True
            print(f"[LSTMForecastModel] ✅ Configurado desde YAML: look_back={self.look_back}, target='{self.target_hint}'")
        except Exception as e:
            print(f"[LSTMForecastModel] ⚠️ Error aplicando configuración YAML ({e}), usando valores por defecto.")
            self._yaml_configured = False

    # --- SELECCIÓN DE COLUMNA ---
    def _to_series(self, data: Any) -> np.ndarray:
        if isinstance(data, pd.DataFrame):
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) == 0:
                raise ValueError("[LSTMForecastModel] ❌ No se encontraron columnas numéricas.")
            
            # 1️⃣ Si YAML define target_hint y existe, úsalo
            if self._yaml_configured and self.target_hint in numeric_cols:
                col = self.target_hint
            else:
                # 2️⃣ Si no, fallback controlado (mayor varianza)
                variances = data[numeric_cols].var()
                col = variances.idxmax()
                print(f"[LSTMForecastModel] ⚠️ Fallback: usando columna '{col}' por mayor varianza.")
            
            data = data[col].values
        elif isinstance(data, pd.Series):
            data = data.values
        elif isinstance(data, list):
            data = np.array(data)
        elif not isinstance(data, np.ndarray):
            raise ValueError(f"[LSTMForecastModel] ❌ Tipo no soportado: {type(data)}")
        return data.astype(float)

    # --- CREACIÓN DE SECUENCIAS ---
    def create_dataset(self, series: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if len(series) <= self.look_back:
            old_lb = self.look_back
            self.look_back = max(1, len(series) // 2)
            print(f"[LSTMForecastModel] ⚠️ Fallback: ajustando look_back de {old_lb} → {self.look_back}")
        X, y = [], []
        for i in range(len(series) - self.look_back):
            X.append(series[i:(i + self.look_back)])
            y.append(series[i + self.look_back])
        return np.array(X), np.array(y)
    
    def _safe_scale(self, series: np.ndarray, fit: bool = False) -> np.ndarray:
        """
        Escalado seguro con fallback automático.
        Si el MinMaxScaler falla (por ejemplo, por valores NaN o forma inválida),
        retorna la serie original sin romper el pipeline.
        """
        try:
            if fit:
                scaled = self.scaler.fit_transform(series.reshape(-1, 1)).flatten()
            else:
                scaled = self.scaler.transform(series.reshape(-1, 1)).flatten()
            return scaled
        except Exception as e:
            print(f"[LSTMForecastModel] ⚠️ Fallback de escalado aplicado: {e}")
            return series

    def _validate_input(self, X, *args, **kwargs):
        """
        Valida y convierte la entrada en un array 1D seguro para secuencias.
        - Acepta DataFrame, Series o arrays.
        - Elimina NaN y asegura forma consistente.
        - Retorna np.ndarray listo para escalar.
        """
        try:
            if isinstance(X, pd.DataFrame):
                numeric_cols = X.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) == 0:
                    raise ValueError("[LSTMForecastModel] No hay columnas numéricas válidas.")
                X = X[numeric_cols[0]]
            if isinstance(X, pd.Series):
                X = X.values
            if not isinstance(X, np.ndarray):
                X = np.array(X)
            X = X[~np.isnan(X)]  # elimina NaN
            return X.flatten()
        except Exception as e:
            print(f"[LSTMForecastModel] ⚠️ Error de validación de entrada: {e}")
            raise


    # --- ENTRENAMIENTO ---
    def train(self, X_train, y_train, X_test, y_test, params):
        self.configure_from_yaml(params, getattr(y_train, "name", None))

        series_train = self._safe_scale(self._to_series(X_train), fit=True)
        series_test = self._safe_scale(self._to_series(X_test), fit=False)

        X_seq, y_seq = self.create_dataset(series_train)
        self._validate_input(X_seq, "entrenamiento")
        X_seq = X_seq.reshape((X_seq.shape[0], X_seq.shape[1], 1))

        self.model = Sequential([
            Input(shape=(self.look_back, 1)),
            LSTM(params.get("units", 50)),
            Dense(1)
        ])
        self.model.compile(
            optimizer=Adam(learning_rate=params.get("learning_rate", 0.001)),
            loss="mse"
        )

        self.model.fit(
            X_seq, y_seq,
            epochs=params.get("epochs", 20),
            batch_size=params.get("batch_size", 16),
            verbose=0
        )

        X_test_seq, y_test_seq = self.create_dataset(series_test)
        self._validate_input(X_test_seq, "evaluación")
        X_test_seq = X_test_seq.reshape((X_test_seq.shape[0], X_test_seq.shape[1], 1))

        y_pred = self.model.predict(X_test_seq, verbose=0).flatten()
        metrics = evaluate_regression(y_test_seq, y_pred, metric_names=params.get("metrics"))
        return self.model, y_pred, metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        try:
            X = self._validate_input(X)
    
            # 🔍 Validación fuerte de longitud
            if X is None or len(X) == 0:
                raise ValueError("[LSTMForecastModel] Entrada vacía: no hay datos para predecir.")
            if len(X) <= self.look_back:
                raise ValueError(
                    f"[LSTMForecastModel] El tamaño de entrada ({len(X)}) es menor o igual al look_back ({self.look_back})."
                )
    
            # 🔧 Escalado seguro
            scaled_input = self._safe_scale(X, fit=False)
            if scaled_input is None or len(scaled_input) == 0:
                raise ValueError("[LSTMForecastModel] Escalado fallido o datos vacíos tras escalar.")
    
            # 🔁 Creación de secuencias
            X_seq, _ = self.create_dataset(scaled_input)
            if X_seq is None or X_seq.size == 0:
                raise ValueError("[LSTMForecastModel] No se generaron secuencias válidas para predicción.")
    
            # 🔢 Validación del shape antes del reshape
            if len(X_seq.shape) != 2:
                raise ValueError(f"[LSTMForecastModel] Forma inesperada: {X_seq.shape}, se esperaba (samples, look_back)")
    
            X_seq = X_seq.reshape((X_seq.shape[0], X_seq.shape[1], 1))
    
            # 🧠 Predicción
            preds = self.model.predict(X_seq, verbose=0)
    
            # 🔄 Normalización de salida
            if not isinstance(preds, np.ndarray):
                preds = np.array(preds)
            preds = preds.flatten()
    
            print(f"[LSTMForecastModel] ✅ Predicciones generadas con forma: {preds.shape}")
            return preds
    
        except Exception as e:
            raise RuntimeError(f"Error durante predicción: {e}")
