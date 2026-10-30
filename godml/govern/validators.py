# compliance_service/validators.py

from typing import List
from godml.core.config.schema import PipelineDefinition
from godml.govern.compliance.validation_helpers import validate_pipeline


def run_validations(pipeline: PipelineDefinition) -> List[str]:
    """
    Ejecuta todas las validaciones de gobernanza y compliance.
    Retorna advertencias. Lanza excepción si hay errores críticos.
    """
    return validate_pipeline(pipeline)
