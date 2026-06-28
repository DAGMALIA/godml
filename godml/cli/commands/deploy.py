from __future__ import annotations

import importlib.resources as pkg_resources
import os
import subprocess
from pathlib import Path
from shutil import which, copytree
from subprocess import CalledProcessError

import typer

from godml.monitoring_service.logger import get_logger, SecurityError
from godml.utils.path_utils import sanitize_for_log, validate_safe_path
from godml.utils.yaml_utils import generate_dockerfile_txt
from ..validators import load_yaml_config, validate_docker_available, validate_docker_tag, validate_environment_vars

logger = get_logger()


def find_model_for_deploy(environment: str) -> Path:
    if ".." in environment or os.path.isabs(environment):
        raise SecurityError("Ambiente no permitido")

    current_dir = Path.cwd()
    search_paths = [current_dir / "models" / environment, current_dir / "models"]

    for search_path in search_paths:
        if search_path.exists():
            for pattern in ["*.pkl", "*model*", "*.joblib", "*.pickle"]:
                for model_file in search_path.glob(pattern):
                    if model_file.is_file():
                        logger.info(f"Modelo encontrado: {sanitize_for_log(str(model_file))}")
                        return model_file

    raise FileNotFoundError(f"No se encontró modelo para ambiente '{sanitize_for_log(environment)}'")


def deploy_command(project_name: str, environment: str) -> None:
    try:
        if ".." in project_name or os.path.isabs(project_name):
            raise SecurityError("Nombre de proyecto no permitido")
        if ".." in environment or os.path.isabs(environment):
            raise SecurityError("Ambiente no permitido")

        validate_docker_available()

        config_yaml = load_yaml_config("godml.yml")
        envs = config_yaml.get("deploy_config", {})

        if environment not in envs:
            available = ", ".join(envs.keys())
            logger.error(f"Ambiente no encontrado: '{sanitize_for_log(environment)}'. Disponibles: {available}")
            raise typer.Exit(1)

        config = envs[environment]
        tag = config.get("docker_tag", f"godml:{environment}")
        port = config.get("port", 8000)
        host = config.get("host", "0.0.0.0")

        safe_tag = validate_docker_tag(tag)
        safe_environment, safe_host, safe_port = validate_environment_vars(environment, host, port)

        deploy_path = validate_safe_path("deploy_service")
        if not Path(deploy_path).exists():
            logger.info("Generando deploy_service desde plantilla...")
            with pkg_resources.path("godml.templates.deploy_template", "") as template_path:
                safe_template_path = validate_safe_path(str(template_path))
                copytree(str(safe_template_path), str(deploy_path))

        dockerfile_path = validate_safe_path("Dockerfile")
        if not Path(dockerfile_path).exists():
            with open(dockerfile_path, "w", encoding="utf-8") as f:
                f.write(generate_dockerfile_txt())

        docker_path = which("docker")
        if docker_path:
            build_timeout = int(os.environ.get("GODML_DOCKER_BUILD_TIMEOUT", "600"))
            run_timeout = int(os.environ.get("GODML_DOCKER_RUN_TIMEOUT", "3600"))

            logger.info(f"Construyendo imagen Docker para {sanitize_for_log(environment)}...")
            try:
                subprocess.run(
                    [docker_path, "build", "-t", safe_tag, "."],
                    check=True,
                    timeout=build_timeout,
                )
            except subprocess.TimeoutExpired:
                logger.error(f"Docker build supero el timeout de {build_timeout}s")
                raise typer.Exit(1)

            logger.info(f"Ejecutando contenedor {sanitize_for_log(safe_tag)}...")
            try:
                subprocess.run([
                    docker_path, "run", "--rm",
                    "-e", f"GODML_ENV={safe_environment}",
                    "-e", f"HOST={safe_host}",
                    "-e", f"PORT={safe_port}",
                    "-p", f"{safe_port}:{safe_port}",
                    safe_tag,
                ], check=True, timeout=run_timeout)
            except subprocess.TimeoutExpired:
                logger.error(f"Docker run supero el timeout de {run_timeout}s")
                raise typer.Exit(1)

    except CalledProcessError as e:
        logger.error(f"Error ejecutando Docker: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except SecurityError as e:
        logger.error(f"Error de seguridad: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Error general: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
