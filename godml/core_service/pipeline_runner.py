# core_service/pipeline_runner.py

from godml.config_service.schema import PipelineDefinition
from godml.core_service.preprocessor import ComplianceEngine
import pandas as pd


def run_pipeline_preprocessing(pipeline: PipelineDefinition, df: pd.DataFrame) -> pd.DataFrame:
    """
    Procesamiento previo al entrenamiento, incluyendo cumplimiento normativo si se especifica.
    """
    if hasattr(pipeline, "governance") and getattr(pipeline.governance, "compliance", None):
        print(f"🔐 Aplicando cumplimiento: {pipeline.governance.compliance}")
        df = ComplianceEngine.apply(df, pipeline.governance.compliance)

    return df
