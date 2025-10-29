# core_service/run_pipeline.py

import os
import logging
from godml.config_service.loader import load_config
from godml.core_service.executors import get_executor
from godml.monitoring_service.logger import godml_logger, PipelineError, ConfigurationError

# Silenciar logs molestos de SageMaker y boto3
logging.getLogger("sagemaker").setLevel(logging.ERROR)
logging.getLogger("boto3").setLevel(logging.ERROR)
logging.getLogger("botocore").setLevel(logging.ERROR)


def display_pipeline_summary(info, metrics):
    """Salida final del pipeline GODML sin Rich, usando el logger limpio."""
    godml_logger.info("\n╭─────────────────────────── GODML ────────────────────────────╮")
    godml_logger.info("│ 🤖 GODML PIPELINE EXECUTION                                  │")
    godml_logger.info("│ Governed, Observable & Declarative Machine Learning (v1.0.2) │")
    godml_logger.info("╰─────────────────────── Dagmalia Labs ────────────────────────╯")

    godml_logger.info("\n📄 YAML Configuration")
    godml_logger.info("───────────────────────────────────────────────────────────────")
    godml_logger.info(f"Path: {info.get('yaml_path', '-')}")
    godml_logger.info("✅ Pipeline loaded successfully")

    godml_logger.info("\n📂 Dataset")
    godml_logger.info("───────────────────────────────────────────────────────────────")
    godml_logger.info(f"Input : {info.get('dataset_path', '-')}")
    godml_logger.info(f"Output: {info.get('output_path', '-')}")
    godml_logger.info(f"Target: {info.get('target', '-')}")

    godml_logger.info("\n⚙️  Model")
    godml_logger.info("───────────────────────────────────────────────────────────────")
    godml_logger.info(f"Type : {info.get('model_type', '-')}")
    godml_logger.info(f"Origin: {info.get('model_source', '-')}")
    godml_logger.info("✅ Model loaded successfully")

    godml_logger.info("\n🚀 Training Process")
    godml_logger.info("───────────────────────────────────────────────────────────────")
    godml_logger.info(f"MLflow Run : {info.get('mlflow_run', '-')}")
    godml_logger.info(f"Working Dir: {info.get('cwd', '-')}")
    godml_logger.info(f"Dataset URI: {info.get('dataset_uri', '-')}")

    godml_logger.info("\n📊 Metrics")
    godml_logger.info("───────────────────────────────────────────────────────────────")
    if metrics:
        for m, v in metrics.items():
            godml_logger.info(f"  • {m:<10} : {v:.4f}" if isinstance(v, float) else f"  • {m:<10} : {v}")
    else:
        godml_logger.info("  (no metrics reported)")

    godml_logger.info("\n✅ Training completed successfully")
    if info.get("model_name"):
        godml_logger.info(f"✅ Model registered: {info['model_name']}")
    if info.get("output_path"):
        godml_logger.info(f"📦 Predictions saved to: {info['output_path']}")
    godml_logger.info("───────────────────────────────────────────────────────────────\n")


def run_pipeline(config_path="godml.yml"):
    """Ejecución completa del pipeline GODML sin Rich y con formato unificado."""
    try:
        godml_logger.info("\n╭─────────────────────────── GODML ────────────────────────────╮")
        godml_logger.info("│ 🚀 STARTING PIPELINE EXECUTION                              │")
        godml_logger.info("│ Governed, Observable & Declarative Machine Learning (v1.0.2) │")
        godml_logger.info("╰─────────────────────── Dagmalia Labs ────────────────────────╯")

        godml_logger.info(f"\n📄 Usando archivo de configuración: {config_path}")

        # 1️⃣ Cargar configuración
        try:
            config = load_config(config_path)
        except FileNotFoundError:
            raise ConfigurationError(f"Archivo de configuración no encontrado: {config_path}")
        except Exception as e:
            raise ConfigurationError(f"Error cargando configuración: {e}")

        # 2️⃣ Obtener executor
        try:
            executor = get_executor(config.provider)
        except ValueError as e:
            raise ConfigurationError(f"Provider no soportado: {e}")
        except Exception as e:
            raise PipelineError(f"Error obteniendo executor: {e}")

        # 3️⃣ Validar configuración (sin log redundante del modelo)
        try:
            logging.getLogger("GODML").setLevel(logging.WARNING)  # silencio temporal
            executor.validate(config)
            logging.getLogger("GODML").setLevel(logging.INFO)
        except Exception as e:
            raise PipelineError(f"Error validando configuración: {e}")

        # 4️⃣ Ejecutar pipeline principal
        try:
            result = executor.run(config)
            godml_logger.info("✅ Pipeline completado exitosamente")

            # Mostrar resumen final si hay métricas
            if hasattr(result, "metrics"):
                pipeline_info = {
                    "yaml_path": config_path,
                    "dataset_path": getattr(config.dataset, "uri", None),
                    "output_path": getattr(config.deploy, "batch_output", None)
                    if getattr(config, "deploy", None)
                    else None,
                    "target": getattr(config.dataset, "target", None),
                    "model_type": getattr(config.model, "type", None),
                    "model_source": getattr(config.model, "source", None),
                    "mlflow_run": getattr(config, "name", None),
                    "cwd": os.getcwd(),
                    "dataset_uri": getattr(config.dataset, "uri", None),
                    "model_name": f"{getattr(config, 'name', 'unnamed')}-{getattr(config.model, 'type', '')}",
                }
                display_pipeline_summary(pipeline_info, result.metrics)
            else:
                godml_logger.warning("⚠️ El executor no retornó métricas; mostrando logs estándar.")
            
            godml_logger.info("\n📈 Final del pipeline")
            godml_logger.info("────────────────────────────────────────")
            godml_logger.info(f"  • Estado   : ✅ Éxito")
            godml_logger.info(f"  • Modelo   : {pipeline_info.get('model_name', '-')}")
            if result.metrics and 'auc' in result.metrics:
                godml_logger.info(f"  • AUC      : {result.metrics.get('auc'):.4f}")
            if pipeline_info.get('output_path'):
                godml_logger.info(f"  • Output   : {pipeline_info['output_path']}")
            godml_logger.info("────────────────────────────────────────\n")

        except Exception as e:
            raise PipelineError(f"Error ejecutando pipeline: {e}")

    except (ConfigurationError, PipelineError):
        raise
    except Exception as e:
        raise PipelineError(f"Error inesperado en pipeline: {e}")
