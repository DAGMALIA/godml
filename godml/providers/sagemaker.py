"""
SageMaker executor — EXPERIMENTAL.

Requires: pip install godml[aws]
Supports: XGBoost only (other model types raise NotImplementedError).

Required environment variables:
  GODML_SAGEMAKER_ROLE  — IAM role ARN with SageMaker execution permissions
  AWS_DEFAULT_REGION    — AWS region (default: us-east-1)
"""
from __future__ import annotations

import os

from godml.core_service.engine import BaseExecutor
from godml.config_service.schema import PipelineDefinition


def _require_aws() -> None:
    try:
        import boto3  # noqa: F401
        import sagemaker  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "SageMaker support requires AWS extras. "
            "Install with: pip install godml[aws]"
        ) from e


class SageMakerExecutor(BaseExecutor):
    """Experimental SageMaker executor. Only XGBoost is currently supported."""

    def __init__(self, region_name: str | None = None):
        _require_aws()
        from sagemaker.session import Session

        self.region = region_name or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self.session = Session()
        self.role = self._get_execution_role()

    def _get_execution_role(self) -> str:
        role = os.environ.get("GODML_SAGEMAKER_ROLE")
        if role:
            return role
        try:
            import sagemaker
            return sagemaker.get_execution_role()
        except Exception:
            raise EnvironmentError(
                "No se encontro un IAM role para SageMaker. "
                "Define la variable de entorno GODML_SAGEMAKER_ROLE con el ARN del rol."
            )

    def run(self, pipeline: PipelineDefinition):
        _require_aws()
        from sagemaker import image_uris
        from sagemaker.model import Model
        from sagemaker.estimator import Estimator
        from sagemaker.inputs import TrainingInput

        print(f"Iniciando entrenamiento en SageMaker: {pipeline.name}")

        if pipeline.model.type.lower() != "xgboost":
            raise NotImplementedError(
                f"SageMaker executor solo soporta XGBoost. "
                f"Tipo recibido: {pipeline.model.type}"
            )

        container_uri = image_uris.retrieve(
            framework="xgboost",
            region=self.region,
            version="1.5-1",
        )

        output_path = f"s3://{self.session.default_bucket()}/godml-outputs/{pipeline.name}/"

        estimator = Estimator(
            image_uri=container_uri,
            role=self.role,
            instance_count=1,
            instance_type="ml.m5.large",
            output_path=output_path,
            sagemaker_session=self.session,
            hyperparameters=pipeline.model.hyperparameters.model_dump(exclude_none=True),
        )

        job_name = f"{pipeline.name.replace('_', '-')}-train"
        estimator.fit(
            {"train": TrainingInput(pipeline.dataset.uri, content_type="text/csv")},
            job_name=job_name,
        )

        print("Entrenamiento completado.")

        if not pipeline.deploy.realtime:
            print("Iniciando inferencia por lotes...")
            model = Model(
                image_uri=container_uri,
                model_data=estimator.model_data,
                role=self.role,
                sagemaker_session=self.session,
            )
            model.create(instance_type="ml.m5.large")
            model.transformer(
                instance_count=1,
                instance_type="ml.m5.large",
                output_path=pipeline.deploy.batch_output,
                accept="text/csv",
                strategy="SingleRecord",
            ).transform(
                data=pipeline.dataset.uri,
                content_type="text/csv",
                split_type="Line",
                job_name=f"{pipeline.name.replace('_', '-')}-batch",
                wait=True,
            )
            print(f"Inference completada. Resultados en: {pipeline.deploy.batch_output}")

    def validate(self, pipeline: PipelineDefinition) -> None:
        try:
            from godml.core_service.validators import validate_pipeline
            warnings = validate_pipeline(pipeline)
            for w in warnings:
                print(f"Advertencia: {w}")
        except ImportError:
            pass
