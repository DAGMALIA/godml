from __future__ import annotations

import logging

from godml.config_service.schema import PipelineDefinition
from godml.core_service.parser import load_pipeline
from godml.core_service.executors import get_executor
from godml.utils.model_storage import save_model_to_structure, load_model_from_structure

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GodmlNotebook:
    def __init__(self):
        self.pipeline = None
        self.last_trained_model = None

    def create_pipeline(
        self,
        name: str,
        model_type: str,
        hyperparameters: dict,
        dataset_path: str,
        target: str | None = None,
        output_path: str | None = None,
    ):
        config = {
            "name": name,
            "version": "1.0.0",
            "provider": "mlflow",
            "dataset": {"uri": dataset_path, "hash": "auto", "target": target},
            "model": {"type": model_type, "hyperparameters": hyperparameters},
            "metrics": [{"name": "auc", "threshold": 0.8}],
            "governance": {
                "owner": "notebook-user@company.com",
                "tags": [{"source": "jupyter"}],
            },
            "deploy": {
                "realtime": False,
                "batch_output": output_path or f"./outputs/{name}_predictions.csv",
            },
        }
        self.pipeline = PipelineDefinition(**config)
        return self.pipeline

    def train(self):
        if not self.pipeline:
            raise ValueError("Primero crea un pipeline")
        executor = get_executor(self.pipeline.provider)
        result = executor.run(self.pipeline)
        try:
            self.last_trained_model = getattr(result, "model", None)
        except Exception:
            self.last_trained_model = None
        return "Entrenamiento completado"

    def save_model(self, model=None, model_name: str | None = None, environment: str = "experiments"):
        model_to_save = model or self.last_trained_model
        if model_to_save is None:
            raise ValueError("No hay modelo para guardar. Entrena un modelo primero o proporciona uno.")
        return save_model_to_structure(model_to_save, model_name, environment)

    def load_model(self, model_name: str, environment: str = "production"):
        return load_model_from_structure(model_name, environment)


def quick_train(
    model_type: str,
    hyperparameters: dict,
    dataset_path: str,
    target: str | None = None,
    name: str | None = None,
):
    godml = GodmlNotebook()
    name = name or f"{model_type}-quick-train"
    godml.create_pipeline(
        name=name,
        model_type=model_type,
        hyperparameters=hyperparameters,
        dataset_path=dataset_path,
        target=target,
    )
    godml.train()
    return "Modelo entrenado exitosamente"


def quick_train_with_metrics(
    model_type: str,
    hyperparameters: dict,
    dataset_path: str,
    target: str | None = None,
    name: str | None = None,
):
    godml = GodmlNotebook()
    name = name or f"{model_type}-quick-train"
    pipe = godml.create_pipeline(
        name=name,
        model_type=model_type,
        hyperparameters=hyperparameters,
        dataset_path=dataset_path,
        target=target,
    )
    executor = get_executor(pipe.provider)
    result = executor.run(pipe)
    return {
        "message": f"Modelo {model_type} entrenado",
        "metrics": getattr(result, "metrics", {}),
        "model": getattr(result, "model", None),
        "pipeline": pipe,
    }


def train_from_yaml(yaml_path: str = "./godml/godml.yml"):
    try:
        pipeline = load_pipeline(yaml_path)
        executor = get_executor(pipeline.provider)
        executor.run(pipeline)
        return f"Modelo {pipeline.model.type} entrenado desde {yaml_path}"
    except Exception as e:
        return f"Error: {e}"


def quick_train_yaml(
    model_type: str, hyperparameters: dict, yaml_path: str = "./godml/godml.yml"
):
    try:
        pipeline = load_pipeline(yaml_path)
        pipeline.model.type = model_type
        try:
            hp_cls = type(pipeline.model.hyperparameters)
            pipeline.model.hyperparameters = hp_cls(**hyperparameters)
        except Exception:
            pipeline.model.hyperparameters = hyperparameters
        pipeline.name = f"{pipeline.name}-{model_type}"
        executor = get_executor(pipeline.provider)
        executor.run(pipeline)
        return f"Modelo {model_type} entrenado con configuración de {yaml_path}"
    except Exception as e:
        return f"Error: {e}"
