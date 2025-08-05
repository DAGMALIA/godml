from sklearn.base import BaseEstimator
from xgboost import Booster as XGBBooster, DMatrix as XGBDMatrix
from lightgbm import Booster as LGBMBooster
from tensorflow.keras.models import Model as KerasModel

def predict_safely(model, input_data):
    """
    Predice usando el tipo de entrada adecuado según el framework del modelo.

    Soporta:
    - XGBoost
    - LightGBM
    - scikit-learn
    - Keras
    """
    if isinstance(model, XGBBooster):
        return model.predict(XGBDMatrix(input_data))
    elif isinstance(model, LGBMBooster):
        return model.predict(input_data)
    elif isinstance(model, BaseEstimator):  # sklearn
        return model.predict(input_data)
    elif isinstance(model, KerasModel):
        return model.predict(input_data)
    else:
        raise TypeError(f"❌ Tipo de modelo no soportado para predicción: {type(model)}")