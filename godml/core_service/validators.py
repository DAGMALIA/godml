# compliance_service/validators.py

from typing import List
from godml.config_service.schema import PipelineDefinition
from godml.compliance_service.validation_helpers import (
    validate_pipeline,
    ValidationError
)


def run_validations(pipeline: PipelineDefinition) -> List[str]:
    """
    Ejecuta todas las validaciones de gobernanza y compliance.
    Retorna advertencias. Lanza excepción si hay errores críticos.
    """
    return validate_pipeline(pipeline)
