from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from shutil import which
from subprocess import DEVNULL, CalledProcessError

import typer
from yaml import safe_load

from godml.monitoring_service.logger import get_logger, SecurityError
from godml.utils.path_utils import sanitize_for_log, validate_safe_path

logger = get_logger()

# Directories that are always considered safe for absolute paths.
# Resolved at import time so they reflect the actual runtime CWD.
_SAFE_BASE_DIRS: list[Path] = [
    Path.cwd().resolve(),
    Path.home().resolve(),
]


def _is_safe_absolute_path(path: str) -> bool:
    """Cross-platform check: absolute path must be under a known-safe base dir."""
    try:
        resolved = Path(path).resolve()
        return any(
            str(resolved).startswith(str(base))
            for base in _SAFE_BASE_DIRS
        )
    except Exception:
        return False


def validate_docker_available() -> None:
    docker_path = which("docker")
    if docker_path is None:
        logger.error("Docker no esta instalado o no esta en PATH.")
        raise typer.Exit(1)

    try:
        if docker_path and (".." in docker_path or not os.path.isabs(docker_path)):
            raise SecurityError("Ruta Docker no segura")
        subprocess.run([docker_path, "info"], stdout=DEVNULL, stderr=DEVNULL, check=True, timeout=10)
    except CalledProcessError:
        logger.error("Docker no esta corriendo.")
        raise typer.Exit(1)
    except subprocess.TimeoutExpired:
        logger.error("Docker no respondio a tiempo.")
        raise typer.Exit(1)


def load_yaml_config(yaml_path: str) -> dict:
    if ".." in yaml_path:
        raise SecurityError("Ruta no permitida")

    if os.path.isabs(yaml_path) and not _is_safe_absolute_path(yaml_path):
        raise SecurityError(f"Ruta absoluta fuera de directorio permitido: {yaml_path}")

    safe_path = validate_safe_path(yaml_path)
    if not safe_path.exists():
        logger.error(f"No se encontro {sanitize_for_log(yaml_path)} en el directorio actual.")
        raise typer.Exit(1)

    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            return safe_load(f)
    except (IOError, OSError) as e:
        logger.error(f"Error leyendo archivo YAML: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)


def validate_docker_tag(tag: str) -> str:
    safe_tag = re.sub(r"[^a-zA-Z0-9:._-]", "", tag)
    if not re.match(r"^[a-zA-Z0-9:._-]+$", safe_tag):
        raise SecurityError(f"Tag Docker invalido: {sanitize_for_log(safe_tag)}")
    return safe_tag


def validate_environment_vars(environment: str, host: str, port: str) -> tuple[str, str, str]:
    safe_environment = re.sub(r"[^a-zA-Z0-9_-]", "", environment)
    safe_host = re.sub(r"[^a-zA-Z0-9._-]", "", str(host))
    safe_port = re.sub(r"[^0-9]", "", str(port))

    if not all([safe_environment, safe_host, safe_port]):
        raise SecurityError("Variables de entorno contienen caracteres invalidos")
    if not re.match(r"^[0-9]+$", safe_port):
        raise SecurityError("Puerto invalido")

    return safe_environment, safe_host, safe_port
