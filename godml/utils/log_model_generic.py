import os
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import mlflow.lightgbm
import mlflow.keras

from sklearn.base import BaseEstimator
from godml.monitoring_service.logger import get_logger
from xgboost import Booster as XGBBooster
from lightgbm import Booster as LGBMBooster
from tensorflow.keras.models import Model as KerasModel


logger = get_logger()

# Verificación inicial: si URI es inválida o apunta a Windows, aplicar fallback local
def ensure_valid_tracking_uri():
    uri = mlflow.get_tracking_uri()
    if not uri or uri.startswith("file:/C:") or "C:/" in uri:
        mlflow.set_tracking_uri("file:./mlruns")
        print("⚠️ Tracking URI inválido detectado. Se usará './mlruns'")
    return mlflow.get_tracking_uri()


# Logueo genérico del modelo, usando argumentos modernos de MLflow
def log_model_generic(
    model,
    model_name: str = "model",
    registered_model_name: str = None,
    input_example=None,
    signature=None
):
    """
    Registra un modelo automáticamente según su tipo en MLflow.

    Args:
        model: modelo ya entrenado (XGBoost, LightGBM, sklearn, Keras).
        model_name (str): Nombre del modelo para los artefactos.
        registered_model_name (str): Nombre para registrar el modelo en el model registry.
        input_example: Ejemplo de entrada para ayudar con la inferencia.
        signature: Objeto `ModelSignature` para definir input/output del modelo.
    """
    ensure_valid_tracking_uri()

    # Argumentos comunes
    log_args = {
        "name": model_name,
        "registered_model_name": registered_model_name,
        "input_example": input_example,
        "signature": signature,
    }

    # Enrutamiento automático por tipo de modelo
    if isinstance(model, XGBBooster):
        mlflow.xgboost.log_model(model, **log_args)
    elif isinstance(model, LGBMBooster):
        mlflow.lightgbm.log_model(model, **log_args)
    elif isinstance(model, BaseEstimator):
        mlflow.sklearn.log_model(sk_model=model, **log_args)
    elif isinstance(model, KerasModel):
        mlflow.keras.log_model(model, **log_args)
    else:
        raise NotImplementedError(f"Modelo de tipo {type(model)} no soportado por log_model_generic.")

    print(f"✅ Modelo registrado con éxito: {registered_model_name or model_name}")