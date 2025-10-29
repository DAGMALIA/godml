# model_registry.py
from godml.model_service.model_registry.random_forest_model import RandomForestModel
from godml.model_service.model_registry.xgboost_model import XgboostModel
from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel
#from godml.model_service.model_registry.lightgbm_model import LightGBMModel
from godml.model_service.model_registry.lstm_forecast_model import LstmForecastModel

model_registry = {
    "random_forest": RandomForestModel,
    "xgboost": XgboostModel,
    "logistic_regression": LogisticRegressionModel,
    "lstm_forecast": LstmForecastModel
}
