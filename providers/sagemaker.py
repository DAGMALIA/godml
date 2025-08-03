import boto3
from sagemaker import image_uris
from sagemaker.model import Model
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from godml.core.engine import BaseExecutor
from godml.core.models import PipelineDefinition


class SageMakerExecutor(BaseExecutor):
    def __init__(self, region_name="us-east-1"):
        self.region = region_name
        self.session = self._create_session()
        self.role = self._get_execution_role()

    def _create_session(self):
        from sagemaker.session import Session
        return Session()

    def _get_execution_role(self) -> str:
        """Devuelve el ARN del rol con permisos para SageMaker"""
        # Puedes parametrizar esto o usar secrets/env vars según tu entorno
        return "arn:aws:iam::123456789012:role/SageMakerExecutionRole"

    def run(self, pipeline: PipelineDefinition):
        print(f"🚀 Iniciando entrenamiento en SageMaker: {pipeline.name}")

        if pipeline.model.type.lower() != "xgboost":
            raise NotImplementedError("Por ahora solo soportamos modelos XGBoost.")

        # 1. Obtener imagen
        container_uri = image_uris.retrieve(
            framework="xgboost",
            region=self.region,
            version="1.5-1"
        )

        output_path = f"s3://{self.session.default_bucket()}/godml-outputs/{pipeline.name}/"

        # 2. Crear y entrenar
        estimator = Estimator(
            image_uri=container_uri,
            role=self.role,
            instance_count=1,
            instance_type="ml.m5.large",
            output_path=output_path,
            sagemaker_session=self.session,
            hyperparameters=pipeline.model.hyperparameters.dict()
        )

        job_name = f"{pipeline.name.replace('_','-')}-train"
        estimator.fit(
            {
                "train": TrainingInput(pipeline.dataset.uri, content_type="text/csv")
            },
            job_name=job_name
        )

        print("✅ Entrenamiento completado.")

        # 3. Inference por lotes (solo si no es realtime)
        if not pipeline.deploy.realtime:
            print("🧠 Iniciando inferencia por lotes...")

            model_name = f"{pipeline.name}-model"
            model = Model(
                image_uri=container_uri,
                model_data=estimator.model_data,
                role=self.role,
                sagemaker_session=self.session
            )

            # Registrar el modelo
            predictor = model.create(
                instance_type="ml.m5.large"
            )

            # Crear Transform Job
            transform_job_name = f"{pipeline.name.replace('_','-')}-batch"
            model.transformer(
                instance_count=1,
                instance_type="ml.m5.large",
                output_path=pipeline.deploy.batch_output,
                accept="text/csv",
                strategy="SingleRecord"
            ).transform(
                data=pipeline.dataset.uri,
                content_type="text/csv",
                split_type="Line",
                job_name=transform_job_name,
                wait=True
            )

            print(f"✅ Inference completada. Resultados en: {pipeline.deploy.batch_output}")

    def validate(self, pipeline: PipelineDefinition):
        print("🧪 Validando pipeline...")
        from godml.core.validators import validate_pipeline
        warnings = validate_pipeline(pipeline)
        for w in warnings:
            print("⚠️", w)
