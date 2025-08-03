# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from abc import ABC, abstractmethod
from godml.config_service.schema import PipelineDefinition

class BaseExecutor(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def run(self, pipeline: PipelineDefinition):
        """Ejecutar el pipeline completo"""
        pass

    @abstractmethod
    def validate(self, pipeline: PipelineDefinition):
        """Validar gobernanza, métricas, etc."""
        pass
