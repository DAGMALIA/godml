# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from typing import Union
from abc import ABC, abstractmethod
from godml.config_service.schema import PipelineDefinition, ModelResult

class BaseExecutor(ABC):
    @abstractmethod
    def run(self, pipeline: PipelineDefinition) -> Union[ModelResult, bool, None]:
        pass

    @abstractmethod
    def validate(self, pipeline: PipelineDefinition):
        pass