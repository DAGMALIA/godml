from godml.config_service.schema import PipelineDefinition
from typing import List


class ValidationError(Exception):
    pass


def validate_pipeline(pipeline: PipelineDefinition) -> List[str]:
    """
    Ejecuta validaciones de gobernanza y compliance.
    Retorna una lista de advertencias o errores críticos.
    Lanza excepción si la validación falla de forma fatal.
    """

    errors = []
    warnings = []

    # Validar owner
    if not pipeline.governance.owner:
        errors.append("Falta el campo 'governance.owner'.")

    # Validar hash del dataset
    if not pipeline.dataset.hash or pipeline.dataset.hash == "auto":
        warnings.append("Advertencia: 'dataset.hash' está en modo automático. Considera calcularlo manualmente para trazabilidad.")

    # Validar métricas
    for metric in pipeline.metrics:
        if metric.threshold < 0 or metric.threshold > 1:
            errors.append(f"El umbral de la métrica {metric.name} está fuera del rango permitido (0-1).")

    # Validar configuración de despliegue
    if not pipeline.deploy.realtime and not pipeline.deploy.batch_output:
        errors.append("Pipeline batch requiere definir 'deploy.batch_output'.")

    # Validar tags mínimos (ej. cumplimiento)
    tags = pipeline.governance.tags or []
    if not any("compliance:" in tag for tag in tags):
        warnings.append("Advertencia: No se especificó ningún tag de cumplimiento ('compliance:*').")

    if errors:
        raise ValidationError("Errores en la validación del pipeline:\n- " + "\n- ".join(errors))

    return warnings