class HyperparamAdvisor:
    def suggest(self, model_type: str):
        defaults = {
            "random_forest": {"n_estimators": [50, 200], "max_depth": [5, 30]},
            "xgboost": {"eta": [0.01, 0.3], "max_depth": [3, 10]},
            "logistic_regression": {"C": [0.1, 1.0, 10]},
        }
        return defaults.get(model_type, {"note": "No defaults available"})
