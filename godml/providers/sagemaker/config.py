"""Resolves AWS and compute config from a PipelineDefinition."""
from __future__ import annotations

import os
from godml.config_service.schema import PipelineDefinition, ComputeConfig


def resolve_aws(pipeline: PipelineDefinition) -> dict:
    """
    Returns a flat dict with resolved AWS params.
    Values from pipeline.aws (already resolved by the YAML loader via ${VAR} substitution).
    Falls back to env vars when pipeline.aws is not defined.
    """
    if pipeline.aws:
        return {
            "role_arn": pipeline.aws.role_arn,
            "region": pipeline.aws.region,
            "s3_bucket": pipeline.aws.s3_bucket,
            "s3_prefix": pipeline.aws.s3_prefix,
            "kms_key_id": pipeline.aws.kms_key_id,
        }

    # Backwards-compat: no aws: block → use env vars
    role = os.environ.get("GODML_SAGEMAKER_ROLE")
    if not role:
        try:
            import sagemaker
            role = sagemaker.get_execution_role()
        except Exception:
            raise EnvironmentError(
                "No IAM role found. Add 'aws.role_arn' to your godml.yml "
                "or set the GODML_SAGEMAKER_ROLE environment variable."
            )

    s3_bucket = os.environ.get("GODML_S3_BUCKET")
    if not s3_bucket:
        try:
            import sagemaker
            s3_bucket = sagemaker.Session().default_bucket()
        except Exception:
            raise EnvironmentError(
                "No S3 bucket found. Add 'aws.s3_bucket' to your godml.yml "
                "or set the GODML_S3_BUCKET environment variable."
            )

    return {
        "role_arn": role,
        "region": os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        "s3_bucket": s3_bucket,
        "s3_prefix": "godml",
        "kms_key_id": None,
    }


def resolve_compute(pipeline: PipelineDefinition) -> ComputeConfig:
    return pipeline.compute or ComputeConfig()
