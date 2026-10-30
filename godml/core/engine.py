# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT

from typing import Union
from abc import ABC, abstractmethod
from godml.core.config.schema import PipelineDefinition, ModelResult


class BaseExecutor(ABC):
    @abstractmethod
    def run(self, pipeline: PipelineDefinition) -> Union[ModelResult, bool, None]:
        pass

    @abstractmethod
    def validate(self, pipeline: PipelineDefinition):
        pass
