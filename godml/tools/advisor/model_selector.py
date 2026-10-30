class ModelSelector:
    def suggest(self, task_type: str, n_samples: int, n_features: int):
        if task_type == "regression":
            return ["linear_regression", "random_forest"]
        elif task_type == "binary_classification":
            return ["logistic_regression", "random_forest", "xgboost"]
        else:  # multiclase
            return ["random_forest", "xgboost", "lightgbm"]
