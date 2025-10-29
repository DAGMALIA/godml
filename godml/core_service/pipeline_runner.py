# core_service/pipeline_runner.py

from godml.config_service.schema import PipelineDefinition
from godml.core_service.preprocessor import ComplianceEngine
from godml.utils.path_utils import normalize_path, validate_safe_path
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

def run_pipeline_preprocessing(pipeline: PipelineDefinition, df: pd.DataFrame) -> pd.DataFrame:
    """
    Procesamiento previo al entrenamiento, incluyendo cumplimiento normativo si se especifica.
    Si se aplica una norma de cumplimiento, guarda el dataset compliant en la ruta indicada por YAML.
    """
    if not hasattr(pipeline, "governance") or not getattr(pipeline.governance, "compliance", None):
        logger.info("ℹ️ [ComplianceEngine] No se definió cumplimiento en governance.")
        return df

    compliance_type = pipeline.governance.compliance
    policy = getattr(pipeline.governance, "policy", "mask_sensitive")
    logger.info(f"🔒 Aplicando cumplimiento normativo: {compliance_type} (policy={policy})")

    try:
        # ✅ 1. Aplicar cumplimiento in-memory
        df_compliant = ComplianceEngine.apply(df.copy(), compliance_type, policy)

        # ✅ 2. Guardar dataset compliant si está definido en el YAML
        compliant_path = getattr(pipeline.dataset, "compliant_output", None)
        if compliant_path:
            try:
                normalized_path = normalize_path(compliant_path)
                validate_safe_path(normalized_path, base_dir=os.getcwd())

                os.makedirs(os.path.dirname(normalized_path), exist_ok=True)
                df_compliant.to_csv(normalized_path, index=False)
                logger.info(f"✅ Dataset compliant guardado en: {normalized_path}")
            except Exception as e:
                logger.error(f"❌ No se pudo guardar dataset compliant: {e}")
        else:
            logger.warning("⚠️ No se definió 'dataset.compliant_output' en el YAML.")

        return df_compliant

    except Exception as e:
        logger.error(f"❌ Error durante la aplicación del cumplimiento: {e}")
        return df
