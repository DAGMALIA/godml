# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple
import pandas as pd
import numpy as np


class BaseModel(ABC):
    """
    Interfaz base para cualquier modelo en GODML.
    """

    @abstractmethod
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        params: Dict
    ) -> Tuple[Any, np.ndarray, Dict[str, float]]:
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        pass


class BaseClassificationModel(BaseModel):
    """
    Clase base para modelos de clasificación.
    Por ahora no agrega nada extra, pero sirve para claridad y especialización futura.
    """
    task_type: str = "classification"

class BaseRegressionModel(BaseModel):
    """
    Clase base para modelos de regresión.
    """
    task_type: str = "regression"
