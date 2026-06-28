from sklearn.base import BaseEstimator
from xgboost import Booster as XGBBooster, DMatrix as XGBDMatrix
from godml.monitoring_service.logger import PredictionError

try:
    from lightgbm import Booster as LGBMBooster
except ModuleNotFoundError:
    LGBMBooster = None

try:
    from tensorflow.keras.models import Model as KerasModel
except ModuleNotFoundError:
    try:
        from keras.models import Model as KerasModel
    except ModuleNotFoundError:
        KerasModel = None


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
            elif LGBMBooster is not None and isinstance(model, LGBMBooster):
                return model.predict(input_data)
            elif isinstance(model, BaseEstimator):
                return model.predict(input_data)
            elif KerasModel is not None and isinstance(model, KerasModel):
                return model.predict(input_data)
            else:
                raise PredictionError(f"Tipo de modelo no soportado: {type(model)}")
        except Exception as e:
            raise PredictionError(f"Error durante predicción: {e}")

    except PredictionError:
        raise
    except Exception as e:
        raise PredictionError(f"Error inesperado en predicción: {e}")
