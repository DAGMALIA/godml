# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import os
import mlflow
import pandas as pd
from sklearn.model_selection import train_test_split

from godml.core.engine import BaseExecutor
from godml.core.models import PipelineDefinition
from godml.core.executor.model_loader import load_custom_model_class
from godml.utils.logger import get_logger
from godml.utils.path_utils import normalize_path
from godml.utils.predict_safely import predict_safely
from godml.utils.log_model_generic import log_model_generic
from godml.core.metrics import evaluate_binary_classification
from godml.core.models import ModelResult
import mlflow.models.signature

logger = get_logger()


class MLflowExecutor(BaseExecutor):
    def __init__(self, tracking_uri: str = None):
        if tracking_uri:
            if tracking_uri.startswith("file:/"):
                local_path = tracking_uri.replace("file:/", "", 1)
                normalized = normalize_path(local_path)
                tracking_uri = f"file://{normalized}"
            mlflow.set_tracking_uri(tracking_uri)
        else:
            mlflow.set_tracking_uri("file:./mlruns")

        mlflow.set_experiment("godml-experiment")

    def preprocess_for_xgboost(self, df, target_col="target"):
        if target_col not in df.columns:
            raise ValueError("El dataset debe contener una columna llamada 'target'.")
        if df[target_col].dtype == object:
            df[target_col] = df[target_col].map({"Yes": 1, "No": 0})

        y = df[target_col]
        X = df.drop(columns=[target_col])

        cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
        if cat_cols:
            X = pd.get_dummies(X, columns=cat_cols, drop_first=True)
        return X, y

    def run(self, pipeline: PipelineDefinition):
        logger.info(f"🚀 Entrenando modelo con MLflow: {pipeline.name}")

        dataset_path = pipeline.dataset.uri
        if dataset_path.startswith("s3://"):
            raise ValueError("MLflowExecutor solo soporta datasets locales (CSV).")

        df = pd.read_csv(dataset_path)
        X, y = self.preprocess_for_xgboost(df, target_col="target")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=max(0.5, 2 / len(X)), random_state=42, stratify=y
        )

        params = pipeline.model.hyperparameters.model_dump(exclude_none=True)
        model_type = pipeline.model.type.lower()
        project_path = os.getcwd()

        max_attempts = 3
        for attempt in range(max_attempts):
            with mlflow.start_run(run_name=pipeline.name):
                mlflow.log_artifact(dataset_path, artifact_path="dataset")

                mlflow.set_tag("dataset.uri", pipeline.dataset.uri)
                mlflow.set_tag("dataset.version", pipeline.version)
                mlflow.set_tag("version", pipeline.version)
                if hasattr(pipeline, "description"):
                    mlflow.set_tag("description", pipeline.description)
                if hasattr(pipeline.governance, "owner"):
                    mlflow.set_tag("owner", pipeline.governance.owner)
                if hasattr(pipeline.governance, "tags"):
                    for tag_dict in pipeline.governance.tags:
                        for k, v in tag_dict.items():
                            mlflow.set_tag(k, v)

                for param_name, param_value in params.items():
                    mlflow.log_param(param_name, param_value)

                # 👇 Carga dinámica del modelo desde la carpeta 'models/'
                source = getattr(pipeline.model, "source", "local")
                try:
                    model_instance = load_custom_model_class(project_path, model_type, source)
                except Exception as e:
                    logger.error(f"❌ Error al cargar el modelo '{model_type}': {e}")
                    raise

                train_result = model_instance.train(X_train, y_train, X_test, y_test, params)

                if isinstance(train_result, tuple):
                    if len(train_result) == 3:
                        model, preds, metrics_dict = train_result
                    elif len(train_result) == 2:
                        model, preds = train_result
                        metrics_dict = evaluate_binary_classification(y_test, preds)
                    else:
                        raise ValueError("❌ El método 'train' retornó una tupla con longitud inesperada.")
                else:
                    raise ValueError("❌ El método 'train' debe retornar al menos (modelo, predicciones).")


                input_example = X_train.iloc[:5]
                output_example = predict_safely(model, input_example)

                signature = mlflow.models.signature.infer_signature(input_example, output_example)

                y_pred_binary = (preds >= 0.5).astype(int)
                metrics_dict = evaluate_binary_classification(y_test, preds)

                for metric_name, value in metrics_dict.items():
                    mlflow.log_metric(metric_name, value)

                logger.info("📊 Métricas:")
                for k, v in metrics_dict.items():
                    logger.info(f" - {k}: {v:.4f}")

                logger.info(f"✅ Entrenamiento finalizado. AUC: {metrics_dict.get('auc', 0):.4f}")

                all_metrics_passed = True
                for metric in pipeline.metrics:
                    value = metrics_dict.get(metric.name)
                    if value is None:
                        logger.warning(f"⚠️ Métrica '{metric.name}' no fue calculada.")
                        continue
                    if value < metric.threshold:
                        logger.error(f"🚫 {metric.name.upper()} ({value:.4f}) < {metric.threshold}")
                        all_metrics_passed = False

                if all_metrics_passed:
                    log_model_generic(
                        model,
                        model_name="model",
                        registered_model_name=f"{pipeline.name}-{model_type}",
                        input_example=input_example,
                        signature=signature
                    )

                    if pipeline.deploy.batch_output:
                        output_path = os.path.abspath(pipeline.deploy.batch_output)
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        pd.DataFrame({"prediction": preds}).to_csv(output_path, index=False)
                        logger.info(f"📦 Predicciones guardadas en: {output_path}")

                        result = ModelResult(
                            model=model,
                            predictions=preds,
                            metrics=metrics_dict,
                            output_path=output_path
                        )
                        return result

                elif attempt < max_attempts - 1:
                    logger.warning(f"🔁 Reentrenando... (intento {attempt + 2}/{max_attempts})")
                else:
                    logger.error("❌ Reentrenamiento fallido. Las métricas no alcanzaron los umbrales esperados.")
                    logger.info("💡 Sugerencias:")
                    logger.info("   - Ajusta los thresholds en godml.yml")
                    logger.info("   - Mejora la calidad del dataset")
                    logger.info("   - Prueba otros hiperparámetros")
                    return False

    def validate(self, pipeline: PipelineDefinition):
        from godml.core.validators import validate_pipeline
        warnings = validate_pipeline(pipeline)
        for w in warnings:
            print("⚠️", w)
