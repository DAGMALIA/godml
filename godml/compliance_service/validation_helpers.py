# compliance_service/validation_helpers.py

from godml.config_service.schema import PipelineDefinition, Metric
from typing import List, Dict


class ValidationError(Exception):
    pass


def is_valid_owner(owner: str) -> bool:
    return bool(owner and owner.strip())


def is_valid_hash(hash_value: str) -> bool:
    return hash_value and hash_value != "auto"


def validate_metrics(metrics: List[Metric]) -> List[str]:
    errors = []
    for metric in metrics:
        if not (0 <= metric.threshold <= 1):
            errors.append(f"El umbral de la métrica '{metric.name}' está fuera del rango permitido (0-1).")
    return errors


def is_valid_deploy_config(pipeline: PipelineDefinition) -> bool:
    return pipeline.deploy.realtime or bool(pipeline.deploy.batch_output)


def has_compliance_tag(tags: List[Dict[str, str]]) -> bool:
    return any("compliance" in tag and tag["compliance"] for tag in tags)


def validate_pipeline(pipeline: PipelineDefinition) -> List[str]:
    """
    Ejecuta validaciones de gobernanza y compliance.
    Retorna advertencias. Lanza excepción si hay errores críticos.
    """

    errors = []
    warnings = []

    if not is_valid_owner(pipeline.governance.owner):
        errors.append("Falta el campo 'governance.owner'.")

    if not is_valid_hash(pipeline.dataset.hash):
        warnings.append("Advertencia: 'dataset.hash' está en modo automático. Considera calcularlo manualmente para trazabilidad.")

    errors += validate_metrics(pipeline.metrics)

    if not is_valid_deploy_config(pipeline):
        errors.append("Pipeline batch requiere definir 'deploy.batch_output'.")

    if not has_compliance_tag(pipeline.governance.tags or []):
        warnings.append("Advertencia: No se especificó ningún tag de cumplimiento ('compliance:*').")

    if errors:
        raise ValidationError("Errores en la validación del pipeline:\n- " + "\n- ".join(errors))

    return warnings
