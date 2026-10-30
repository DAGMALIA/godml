from sklearn.base import BaseEstimator
from xgboost import Booster as XGBBooster, DMatrix as XGBDMatrix
from godml.core.logger import PredictionError

import sys


def _loaded_class(module: str, *attrs: str):
    """Class from an already-imported optional framework, else None.

    A LightGBM or Keras model can only exist if its framework is already
    imported, so this never imports them (importing TensorFlow changes
    process env vars and is slow; F1-12).
    """
    obj = sys.modules.get(module)
    for attr in attrs:
        obj = getattr(obj, attr, None)
    return obj if isinstance(obj, type) else None


def predict_safely(model, input_data):
    """
    Predice usando el tipo de entrada adecuado según el framework del modelo.

    Soporta: XGBoost, LightGBM, scikit-learn, Keras
    """
    try:
        if model is None:
            raise PredictionError("Modelo no puede ser None")
        if input_data is None:
            raise PredictionError("Datos de entrada no pueden ser None")

        try:
            if len(input_data) == 0:
                raise PredictionError("Datos de entrada están vacíos")
        except TypeError:
            pass

        try:
            if isinstance(model, XGBBooster):
                return model.predict(XGBDMatrix(input_data))
            elif (lgbm := _loaded_class("lightgbm", "Booster")) and isinstance(
                model, lgbm
            ):
                return model.predict(input_data)
            elif isinstance(model, BaseEstimator):
                return model.predict(input_data)
            elif any(
                cls and isinstance(model, cls)
                for cls in (
                    _loaded_class("keras", "Model"),
                    _loaded_class("tensorflow", "keras", "Model"),
                )
            ):
                return model.predict(input_data)
            else:
                raise PredictionError(f"Tipo de modelo no soportado: {type(model)}")
        except Exception as e:  # noqa: BLE001
            raise PredictionError(f"Error durante predicción: {e}")

    except PredictionError:
        raise
    except Exception as e:  # noqa: BLE001
        raise PredictionError(f"Error inesperado en predicción: {e}")
