from __future__ import annotations

import os

import typer
import uvicorn

from godml.monitoring_service.logger import get_logger, SecurityError, ConfigurationError
from godml.utils.path_utils import sanitize_for_log
from ..validators import load_yaml_config

logger = get_logger()


def serve_command(environment: str = "dev") -> None:
    try:
        if ".." in environment or os.path.isabs(environment):
            raise SecurityError("Ambiente no permitido")

        config_yaml = load_yaml_config("godml.yml")
        deploy_config = config_yaml.get("deploy_config", {})

        if environment not in deploy_config:
            logger.error(f"Ambiente '{sanitize_for_log(environment)}' no encontrado en deploy_config.")
            raise typer.Exit(1)

        config = deploy_config[environment]

        missing = [k for k in ["host", "port", "docker_tag"] if k not in config]
        if missing:
            logger.error(f"Faltan claves en 'deploy_config.{sanitize_for_log(environment)}': {', '.join(missing)}")
            raise typer.Exit(1)

        host = config["host"]
        port = config["port"]

        logger.info(f"Sirviendo modelo en http://{sanitize_for_log(str(host))}:{sanitize_for_log(str(port))}")
        uvicorn.run("godml.deploy_service.server:app", host=host, port=port, reload=True)

    except ConfigurationError as e:
        logger.error(f"Error de configuración: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Error en serve: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
