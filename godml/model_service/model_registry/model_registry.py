# model_registry.py
from godml.model_service.model_registry.random_forest_model import RandomForestModel
from godml.model_service.model_registry.xgboost_model import XgboostModel
from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel
from godml.model_service.model_registry.linear_regression_model import LinearRegressionModel
from godml.model_service.model_registry.lstm_forecast_model import LSTMForecastModel

model_registry = {
    "random_forest": RandomForestModel,
    "xgboost": XgboostModel,
    "logistic_regression": LogisticRegressionModel,
    "linear_regression": LinearRegressionModel,
    "lstm_forecast": LSTMForecastModel
}