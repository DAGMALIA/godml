# core_service/run_pipeline.py

from godml.config_service.loader import load_config
from godml.core_service.executors import get_executor
from godml.monitoring_service.logger import godml_logger


def run_pipeline(config_path="godml.yml"):
    config = load_config(config_path)

    executor = get_executor(config.provider)

    godml_logger.info("🚀 Pipeline started")
    executor.validate(config)
    executor.run(config)
