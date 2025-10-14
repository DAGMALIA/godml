# godml/advisor_service/advisor_orchestrator.py

import json
from godml.advisor_service.metric_judge import MetricJudge
from godml.advisor_service.model_selector import ModelSelector
from godml.advisor_service.hyperparam_advisor import HyperparamAdvisor
from godml.advisor_service.data_quality_judge import DataQualityJudge
from godml.advisor_service.rag_advisor import RAGAdvisor


def _json_safe(obj):
    """Convierte objetos no serializables (ej. numpy.int64) en tipos Python estándar."""
    if hasattr(obj, "item"):  # numpy scalar (ej: int64, float32)
        return obj.item()
    raise TypeError(f"Objeto no serializable: {obj}")


class AdvisorOrchestrator:
    def __init__(self, use_rag=True):
        self.metric_judge = MetricJudge()
        self.model_selector = ModelSelector()
        self.hyperparam_advisor = HyperparamAdvisor()
        self.data_quality = DataQualityJudge()
        self.llm_advisor = RAGAdvisor() if use_rag else None

    def analyze(self, df, target: str = None, derive_target: bool = False):
        # 1) Calidad de datos
        quality = self.data_quality.check(df)

        # 2) Métricas y modelos (solo si hay target)
        if target and target in df.columns:
            metrics = self.metric_judge.analyze(df, target)
            models = self.model_selector.suggest(metrics["task_type"], *df.shape)
            hyperparams = self.hyperparam_advisor.suggest(models[1])
        else:
            metrics = {"task_type": "unsupervised", "metrics": []}
            models = []
            hyperparams = {}
            if derive_target:
                if {"precio", "cantidad"}.issubset(df.columns):
                    df["target"] = (df["precio"].fillna(0) * df["cantidad"].fillna(0) > 1000).astype(int)
                    print("⚡ Target derivado automáticamente: 'venta_grande'")
                    metrics = self.metric_judge.analyze(df, "target")
                    models = self.model_selector.suggest(metrics["task_type"], *df.shape)
                    hyperparams = self.hyperparam_advisor.suggest(models[0])

        # 3) LLM / RAG para receta
        dataset_summary = (
            f"{df.shape[0]} filas, "
            f"target {metrics['task_type']}, "
            f"{len(df.select_dtypes(include=['object']).columns)} categóricas, "
            f"nulos: {quality['nulls']}"
        )

        recipe_llm = None
        if self.llm_advisor:
            raw_recipe = self.llm_advisor.suggest_recipe(dataset_summary)
            try:
                # Si viene como string → parseamos directo
                if isinstance(raw_recipe, str):
                    recipe_llm = json.loads(raw_recipe)
                else:
                    # Si ya es dict de Python → lo normalizamos a JSON válido
                    recipe_llm = json.loads(json.dumps(raw_recipe))
            except Exception as e:
                print(f"⚠️ Error validando receta: {e}")
                recipe_llm = {"error": "Receta inválida", "raw": str(raw_recipe)}

        # 4) Imprimir resultados con formato seguro

        print("=== Modelos ===")
        print(json.dumps(models, indent=2, ensure_ascii=False, default=_json_safe))

        print("=== Hyperparams ===")
        print(json.dumps(hyperparams, indent=2, ensure_ascii=False, default=_json_safe))

        print("=== Calidad de datos ===")
        print(json.dumps(quality, indent=2, ensure_ascii=False, default=_json_safe))

        return {
            "models": models,
            "hyperparams": hyperparams,
            "quality": quality,
        }