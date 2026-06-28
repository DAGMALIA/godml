"""SageMaker executor — runs a godml pipeline as a SageMaker Pipeline."""
from __future__ import annotations

from godml.core_service.engine import BaseExecutor
from godml.config_service.schema import PipelineDefinition
from godml.monitoring_service.logger import get_logger

logger = get_logger()

_SUPPORTED_MODELS = {"xgboost", "random_forest", "logistic_regression", "lightgbm"}


def _require_aws() -> None:
    try:
        import boto3  # noqa: F401
        import sagemaker  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "SageMaker support requires AWS extras. "
            "Install with: pip install godml[aws]"
        ) from exc


class SageMakerExecutor(BaseExecutor):
    """
    Executes a godml pipeline as a SageMaker Pipeline (Preprocessing → Training → Evaluation).

    Minimum godml.yml config required:
        provider: sagemaker
        dataset:
          uri: s3://my-bucket/data/train.csv   # must be an S3 URI
        aws:
          role_arn: ${SAGEMAKER_ROLE_ARN}
          region: us-east-1
          s3_bucket: my-bucket
    """

    def validate(self, pipeline: PipelineDefinition) -> None:
        _require_aws()
        errors: list[str] = []

        if not pipeline.dataset.uri.startswith("s3://"):
            errors.append(
                "dataset.uri must be an S3 URI (s3://bucket/path) when using provider: sagemaker."
            )

        if pipeline.aws:
            if not pipeline.aws.role_arn:
                errors.append("aws.role_arn is required.")
            if not pipeline.aws.s3_bucket:
                errors.append("aws.s3_bucket is required.")
        else:
            import os
            if not os.environ.get("GODML_SAGEMAKER_ROLE"):
                errors.append(
                    "No IAM role configured. Add 'aws.role_arn' to your godml.yml "
                    "or set the GODML_SAGEMAKER_ROLE environment variable."
                )

        model_type = pipeline.model.type.lower()
        if model_type not in _SUPPORTED_MODELS:
            errors.append(
                f"model.type '{model_type}' is not supported by the SageMaker executor. "
                f"Supported types: {', '.join(sorted(_SUPPORTED_MODELS))}"
            )

        if errors:
            raise ValueError(
                "SageMaker pipeline validation failed:\n"
                + "\n".join(f"  • {e}" for e in errors)
            )

        logger.info("SageMaker pipeline validation passed.")

    def run(self, pipeline: PipelineDefinition):
        _require_aws()
        from godml.providers.sagemaker.pipeline_builder import build_pipeline

        logger.info(f"Building SageMaker Pipeline: {pipeline.name}")
        sm_pipeline, aws = build_pipeline(pipeline)

        logger.info("Upserting pipeline definition to SageMaker...")
        sm_pipeline.upsert(role_arn=aws["role_arn"])

        logger.info("Starting pipeline execution...")
        execution = sm_pipeline.start()

        logger.info(
            f"Pipeline running. ARN: {execution.arn}\n"
            f"Track at: https://{aws['region']}.console.aws.amazon.com/sagemaker/home"
            f"?region={aws['region']}#/pipelines/{pipeline.name.replace('_', '-')}/executions"
        )
        logger.info("Waiting for pipeline to finish (this may take several minutes)...")

        execution.wait()

        steps_status = execution.list_steps()
        for step in steps_status:
            logger.info(f"  {step['StepName']}: {step['StepStatus']}")

        final_status = execution.describe()["PipelineExecutionStatus"]
        if final_status != "Succeeded":
            raise RuntimeError(
                f"SageMaker Pipeline finished with status: {final_status}. "
                f"ARN: {execution.arn}"
            )

        logger.info(f"Pipeline completed successfully. ARN: {execution.arn}")
        return True
