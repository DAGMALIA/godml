from sklearn.base import BaseEstimator
from xgboost import Booster as XGBBooster, DMatrix as XGBDMatrix
from lightgbm import Booster as LGBMBooster
try:
    # Compatibilidad con TensorFlow < 2.17
    from tensorflow.keras.models import Model as KerasModel
except ModuleNotFoundError:
    # Compatibilidad con TensorFlow >= 2.17 (Keras 3)
    from keras.models import Model as KerasModel
from godml.monitoring_service.logger import PredictionError

def predict_safely(model, input_data):
    """
    Predice usando el tipo de entrada adecuado según el framework del modelo.
    
    Soporta:
    - XGBoost
    - LightGBM  
    - scikit-learn
    - Keras
    """
    try:
        # Validar entradas
        if model is None:
            raise PredictionError("Modelo no puede ser None")
        
        if input_data is None:
            raise PredictionError("Datos de entrada no pueden ser None")
        
        # Verificar que input_data no esté vacío
        try:
            if len(input_data) == 0:
                raise PredictionError("Datos de entrada están vacíos")
        except TypeError:
            # Si no tiene len(), asumir que es válido
            pass
        
        # Predicción según tipo de modelo
        try:
            if isinstance(model, XGBBooster):
                return model.predict(XGBDMatrix(input_data))
            elif isinstance(model, LGBMBooster):
                return model.predict(input_data)
            elif isinstance(model, BaseEstimator):  # sklearn
                return model.predict(input_data)
            elif isinstance(model, KerasModel):
                return model.predict(input_data)
            else:
                raise PredictionError(f"Tipo de modelo no soportado: {type(model)}")
                
        except Exception as e:
            raise PredictionError(f"Error durante predicción: {e}")
            
    except PredictionError:
        raise
    except Exception as e:
        raise PredictionError(f"Error inesperado en predicción: {e}")
