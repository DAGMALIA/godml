import numpy as np
import pandas as pd
from collections import Counter
import json

class MetricJudge:
    def analyze(self, df: pd.DataFrame, target: str, pretty: bool = False):
        y = df[target]
        df.drop(columns=[target])

        # Detectar tipo de tarea
        if np.issubdtype(y.dtype, np.number) and len(np.unique(y)) > 10:
            task_type = "regression"
        elif len(np.unique(y)) == 2:
            task_type = "binary_classification"
        else:
            task_type = "multiclass_classification"

        balance = Counter(y)
        imbalance = max(balance.values()) / min(balance.values()) > 1.5 if len(balance) > 1 else False

        # Reglas de métricas
        if task_type == "regression":
            metrics = ["rmse", "mae", "r2"]
        elif task_type == "binary_classification":
            metrics = ["f1", "auc", "accuracy"] if not imbalance else ["f1", "recall", "auc"]
        else:
            metrics = ["accuracy", "macro_f1"]

        recipe = {
            "inputs": [{"name": "raw", "connector": "dataframe", "uri": None}],
            "steps": [{"op": "drop_duplicates", "params": {}}],
            "outputs": [{"name": "clean", "connector": "dataframe", "uri": None}],
        }

        result = {
            "task_type": task_type,
            "metrics": metrics,
            "recipe": recipe
        }

        if pretty:
            print("\n=== Metric Judge ===")
            print(f"📊 Tipo de tarea: {task_type}")
            print(f"📌 Métricas recomendadas: {', '.join(metrics)}")
            print("📜 Receta mínima de DataPrep:")
            print(json.dumps(recipe, indent=2, ensure_ascii=False))

        return result

