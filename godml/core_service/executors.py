# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from godml.providers.mlflow import MLflowExecutor
from godml.providers.sagemaker import SageMakerExecutor
from godml.monitoring_service.logger import get_logger, ConfigurationError

logger = get_logger()

_providers_map = {
    "mlflow": MLflowExecutor,
    "sagemaker": SageMakerExecutor,
}

def get_executor(provider_name: str):
    try:
        if not provider_name:
            raise ConfigurationError("Nombre de provider no puede estar vacío")
        
        provider = provider_name.lower().strip()
        
        if provider in _providers_map:
            try:
                return _providers_map[provider]()
            except Exception as e:
                raise ConfigurationError(f"Error inicializando executor {provider}: {e}")
        else:
            available = ", ".join(_providers_map.keys())
            raise ConfigurationError(f"Provider '{provider_name}' no soportado. Disponibles: {available}")
            
    except ConfigurationError:
        raise
    except Exception as e:
        raise ConfigurationError(f"Error inesperado obteniendo executor: {e}")
