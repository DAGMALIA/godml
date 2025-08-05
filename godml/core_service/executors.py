# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from godml.providers.mlflow import MLflowExecutor
from godml.providers.sagemaker import SageMakerExecutor
from godml.monitoring_service.logger import get_logger

logger = get_logger()

_providers_map = {
    "mlflow": MLflowExecutor,
    "sagemaker": SageMakerExecutor,
}

def get_executor(provider_name: str):
    provider = provider_name.lower()

    if provider == "mlflow":
        from providers.mlflow import MLflowExecutor
        return MLflowExecutor()
    elif provider == "sagemaker":
        from providers.sagemaker import SageMakerExecutor
        return SageMakerExecutor()
    else:
        raise ValueError(f"Provider '{provider_name}' no soportado.")
