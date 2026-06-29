"""
Builds individual SageMaker Pipeline steps from a PipelineDefinition.

Each function returns one step (or a tuple when auxiliary data is also needed).
The pipeline_builder assembles them into the final Pipeline object.
"""
from __future__ import annotations

from pathlib import Path
from godml.config_service.schema import PipelineDefinition, ComputeConfig

SCRIPTS_DIR = Path(__file__).parent / "scripts"
_SKLEARN_FW = "1.2-1"
_XGBOOST_FW = "1.7-1"


def _sklearn_image(region: str) -> str:
    from sagemaker import image_uris
    return image_uris.retrieve("sklearn", region, version=_SKLEARN_FW)


def build_preprocessing_step(
    pipeline: PipelineDefinition,
    aws: dict,
    compute: ComputeConfig,
    pipeline_session,
):
    """
    ProcessingStep: reads raw S3 data, applies compliance, splits train/test.
    Returns (step, s3_preprocessed_prefix).
    """
    from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput
    from sagemaker.workflow.steps import ProcessingStep

    processor = ScriptProcessor(
        image_uri=_sklearn_image(aws["region"]),
        command=["python3"],
        instance_type=compute.preprocessing,
        instance_count=1,
        role=aws["role_arn"],
        sagemaker_session=pipeline_session,
        env={
            "GODML_PIPELINE_NAME": pipeline.name,
            "GODML_TARGET_COL": getattr(pipeline.dataset, "target", None) or "target",
            "GODML_COMPLIANCE": getattr(pipeline.governance, "compliance", None) or "",
            "GODML_POLICY": getattr(pipeline.governance, "policy", None) or "mask_sensitive",
        },
    )

    s3_out = f"s3://{aws['s3_bucket']}/{aws['s3_prefix']}/{pipeline.name}/preprocessed"

    step = ProcessingStep(
        name="Preprocessing",
        processor=processor,
        code=str(SCRIPTS_DIR / "preprocess.py"),
        inputs=[
            ProcessingInput(
                source=pipeline.dataset.uri,
                destination="/opt/ml/processing/input/data",
            )
        ],
        outputs=[
            ProcessingOutput(
                output_name="train",
                source="/opt/ml/processing/output/train",
                destination=f"{s3_out}/train",
            ),
            ProcessingOutput(
                output_name="test",
                source="/opt/ml/processing/output/test",
                destination=f"{s3_out}/test",
            ),
        ],
    )
    return step, s3_out


def build_training_step(
    pipeline: PipelineDefinition,
    aws: dict,
    compute: ComputeConfig,
    preprocessing_step,
    pipeline_session,
):
    """TrainingStep: trains model using preprocessed train split."""
    from sagemaker.workflow.steps import TrainingStep
    from sagemaker.inputs import TrainingInput

    model_type = pipeline.model.type.lower()
    hyperparams = pipeline.model.hyperparameters.model_dump(exclude_none=True)
    s3_out = f"s3://{aws['s3_bucket']}/{aws['s3_prefix']}/{pipeline.name}/model"

    if model_type == "xgboost":
        from sagemaker.xgboost import XGBoost
        estimator = XGBoost(
            entry_point="train_xgboost.py",
            source_dir=str(SCRIPTS_DIR),
            framework_version=_XGBOOST_FW,
            instance_type=compute.training,
            instance_count=1,
            role=aws["role_arn"],
            output_path=s3_out,
            sagemaker_session=pipeline_session,
            hyperparameters=hyperparams,
        )
    else:
        from sagemaker.sklearn import SKLearn
        estimator = SKLearn(
            entry_point="train_sklearn.py",
            source_dir=str(SCRIPTS_DIR),
            framework_version=_SKLEARN_FW,
            instance_type=compute.training,
            instance_count=1,
            role=aws["role_arn"],
            output_path=s3_out,
            sagemaker_session=pipeline_session,
            hyperparameters={**hyperparams, "model_type": model_type},
        )

    # Use the output of the preprocessing step directly (no hard-coded S3 path)
    train_source = preprocessing_step.properties.Outputs["train"].S3Output.S3Uri

    return TrainingStep(
        name="Training",
        estimator=estimator,
        inputs={"train": TrainingInput(train_source, content_type="text/csv")},
    )


def build_evaluation_step(
    pipeline: PipelineDefinition,
    aws: dict,
    compute: ComputeConfig,
    preprocessing_step,
    training_step,
    pipeline_session,
):
    """
    ProcessingStep: loads model + test split, writes evaluation.json.
    Returns (step, PropertyFile) so the register step can gate on metrics.
    """
    from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput
    from sagemaker.workflow.steps import ProcessingStep
    from sagemaker.workflow.properties import PropertyFile

    processor = ScriptProcessor(
        image_uri=_sklearn_image(aws["region"]),
        command=["python3"],
        instance_type=compute.evaluation,
        instance_count=1,
        role=aws["role_arn"],
        sagemaker_session=pipeline_session,
        env={
            "GODML_MODEL_TYPE": pipeline.model.type.lower(),
            "GODML_TARGET_COL": getattr(pipeline.dataset, "target", None) or "target",
        },
    )

    evaluation_report = PropertyFile(
        name="EvaluationReport",
        output_name="evaluation",
        path="evaluation.json",
    )

    s3_eval = f"s3://{aws['s3_bucket']}/{aws['s3_prefix']}/{pipeline.name}/evaluation"
    test_source = preprocessing_step.properties.Outputs["test"].S3Output.S3Uri

    step = ProcessingStep(
        name="Evaluation",
        processor=processor,
        code=str(SCRIPTS_DIR / "evaluate.py"),
        inputs=[
            ProcessingInput(
                source=training_step.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            ),
            ProcessingInput(
                source=test_source,
                destination="/opt/ml/processing/test",
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="evaluation",
                source="/opt/ml/processing/evaluation",
                destination=s3_eval,
            ),
        ],
        property_files=[evaluation_report],
    )
    return step, evaluation_report


def build_register_step(
    pipeline: PipelineDefinition,
    training_step,
    evaluation_step,
    evaluation_report,
):
    """
    Conditional RegisterModel: only registers if primary metric >= threshold.
    Returns a ConditionStep (or None if no registry config).
    """
    from sagemaker.workflow.step_collections import RegisterModel
    from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
    from sagemaker.workflow.condition_step import ConditionStep
    from sagemaker.workflow.functions import JsonGet

    if not pipeline.registry:
        return None

    approval = "Approved" if pipeline.registry.approval == "auto" else "PendingManualApproval"

    register = RegisterModel(
        name="RegisterModel",
        estimator=training_step.estimator,
        model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.m5.large", "ml.m5.xlarge"],
        transform_instances=["ml.m5.large", "ml.m5.xlarge"],
        model_package_group_name=pipeline.registry.model_package_group,
        approval_status=approval,
    )

    if not pipeline.metrics:
        return register

    primary = pipeline.metrics[0]
    condition = ConditionGreaterThanOrEqualTo(
        left=JsonGet(
            step_name=evaluation_step.name,
            property_file=evaluation_report,
            json_path=primary.name,
        ),
        right=primary.threshold,
    )

    return ConditionStep(
        name="CheckMetricAndRegister",
        conditions=[condition],
        if_steps=[register],
        else_steps=[],
    )
