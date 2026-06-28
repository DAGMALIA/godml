# model_registry.py
from godml.model_service.model_registry.random_forest_model import RandomForestModel
from godml.model_service.model_registry.xgboost_model import XgboostModel
from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel
try:
    from godml.model_service.model_registry.lstm_forecast_model import LstmForecastModel
    _lstm_available = True
except ImportError:
    LstmForecastModel = None
    _lstm_available = False

model_registry = {
    "random_forest": RandomForestModel,
    "xgboost": XgboostModel,
    "logistic_regression": LogisticRegressionModel,
}

if _lstm_available:
    model_registry["lstm_forecast"] = LstmForecastModel
