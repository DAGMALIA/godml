from __future__ import annotations

from godml.monitoring_service.logger import get_logger

logger = get_logger()


def ensure_valid_tracking_uri() -> str:
    import mlflow
    uri = mlflow.get_tracking_uri()
    # MLflow 3.x dropped file-store support: solo redirige URIs `file:`/vacías.
    # OJO: no filtrar por "C:/" — eso pisaba cualquier sqlite:///C:/... absoluto
    # (Windows) a mitad del run, apuntando log_model() a un mlflow.db distinto
    # del que abrió el run activo y causando "Run with id=... not found".
    if not uri or uri.startswith("file:"):
        mlflow.set_tracking_uri("sqlite:///mlflow.db")
    return mlflow.get_tracking_uri()


def log_model_generic(
    model,
    model_name: str = "model",
    registered_model_name: str | None = None,
    input_example=None,
    signature=None,
) -> None:
    """
    Registers a trained model in MLflow, routing by type:
    XGBoost, LightGBM, sklearn BaseEstimator, or Keras Model.
    """
    import mlflow
    import mlflow.sklearn
    import mlflow.xgboost

    ensure_valid_tracking_uri()

    log_args = {
        "name": model_name,
        "registered_model_name": registered_model_name,
        "input_example": input_example,
        "signature": signature,
    }

    try:
        from xgboost import Booster as XGBBooster
        from xgboost.sklearn import XGBModel
        if isinstance(model, XGBBooster):
            # Native XGBoost Booster — use xgboost flavor (no skops involved)
            mlflow.xgboost.log_model(model, **log_args)
            logger.info(f"Modelo XGBoost registrado: {registered_model_name or model_name}")
            return
        if isinstance(model, XGBModel):
            # Sklearn-API XGBoost (XGBClassifier/XGBRegressor) — se registra
            # con el flavor sklearn, igual que cualquier BaseEstimator.
            mlflow.sklearn.log_model(sk_model=model, **log_args)
            logger.info(f"Modelo XGBoost (sklearn API) registrado: {registered_model_name or model_name}")
            return
    except ImportError:
        pass

    try:
        import mlflow.lightgbm
        from lightgbm import Booster as LGBMBooster
        from lightgbm.sklearn import LGBMModel
        if isinstance(model, (LGBMBooster, LGBMModel)):
            mlflow.lightgbm.log_model(model, **log_args)
            logger.info(f"Modelo LightGBM registrado: {registered_model_name or model_name}")
            return
    except ImportError:
        pass

    try:
        from sklearn.base import BaseEstimator
        if isinstance(model, BaseEstimator):
            mlflow.sklearn.log_model(sk_model=model, **log_args)
            logger.info(f"Modelo sklearn registrado: {registered_model_name or model_name}")
            return
    except ImportError:
        pass

    try:
        import mlflow.keras
        try:
            from tensorflow.keras.models import Model as KerasModel
        except ImportError:
            from keras.models import Model as KerasModel
        if isinstance(model, KerasModel):
            mlflow.keras.log_model(model, **log_args)
            logger.info(f"Modelo Keras registrado: {registered_model_name or model_name}")
            return
    except ImportError:
        pass

    raise NotImplementedError(
        f"Tipo de modelo no soportado por log_model_generic: {type(model)}. "
        "Instala el extra correspondiente: godml[deep] para Keras, godml[advisor] para LightGBM."
    )
