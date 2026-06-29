"""Assembles a SageMaker Pipeline from a PipelineDefinition."""
from __future__ import annotations

from godml.config_service.schema import PipelineDefinition
from godml.providers.sagemaker.config import resolve_aws, resolve_compute
from godml.providers.sagemaker import step_builder as sb


def build_pipeline(pipeline: PipelineDefinition):
    """
    Returns (sm_pipeline, aws_dict) ready to upsert and start.

    Steps always built: Preprocessing → Training → Evaluation
    Optional step:      RegisterModel (only when pipeline.registry is defined)
    """
    from sagemaker.workflow.pipeline import Pipeline
    from sagemaker.workflow.pipeline_context import PipelineSession

    aws = resolve_aws(pipeline)
    compute = resolve_compute(pipeline)

    pipeline_session = PipelineSession(
        default_bucket=aws["s3_bucket"],
    )

    # 1. Preprocessing
    preprocessing_step, _ = sb.build_preprocessing_step(
        pipeline, aws, compute, pipeline_session
    )

    # 2. Training (depends on preprocessing outputs)
    training_step = sb.build_training_step(
        pipeline, aws, compute, preprocessing_step, pipeline_session
    )

    # 3. Evaluation (depends on training model artifacts + test split)
    evaluation_step, evaluation_report = sb.build_evaluation_step(
        pipeline, aws, compute, preprocessing_step, training_step, pipeline_session
    )

    steps = [preprocessing_step, training_step, evaluation_step]

    # 4. Register (optional, gated on primary metric threshold)
    register_step = sb.build_register_step(
        pipeline, training_step, evaluation_step, evaluation_report
    )
    if register_step:
        steps.append(register_step)

    sm_pipeline = Pipeline(
        name=pipeline.name.replace("_", "-"),
        steps=steps,
        sagemaker_session=pipeline_session,
    )

    return sm_pipeline, aws
