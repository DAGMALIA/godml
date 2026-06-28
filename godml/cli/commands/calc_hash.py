from __future__ import annotations

import os
from typing import Optional

import typer

from godml.monitoring_service.logger import get_logger, SecurityError
from godml.utils.hash import calculate_file_hash
from godml.utils.path_utils import sanitize_for_log, validate_safe_path
from godml.utils.yaml_utils import update_dataset_hash_in_yaml

logger = get_logger()


def calc_hash_command(path: str, update_yaml: Optional[str] = None) -> None:
    try:
        if ".." in path or os.path.isabs(path):
            raise SecurityError("Ruta no permitida")
        if update_yaml and (".." in update_yaml or os.path.isabs(update_yaml)):
            raise SecurityError("Ruta YAML no permitida")

        full_path = validate_safe_path(path)
        hash_value = calculate_file_hash(str(full_path))
        print(f"Hash SHA-256 para {full_path}:\n{hash_value}")

        if update_yaml:
            yaml_path = validate_safe_path(update_yaml)
            update_dataset_hash_in_yaml(str(yaml_path), hash_value)
            print(f"Hash actualizado en YAML: {yaml_path}")

    except FileNotFoundError as e:
        logger.error(f"Archivo no encontrado: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Error al calcular hash: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
