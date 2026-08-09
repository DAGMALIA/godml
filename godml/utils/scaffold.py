# Copyright (c) 2025 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License
"""
Scaffolding del servicio de inferencia de un proyecto GODML.

`godml init` y `godml deploy` necesitan el mismo `deploy_service/`: init para
que el proyecto quede buildeable desde el arranque, deploy para poder construir
la imagen. Antes solo lo generaba deploy, así que el Dockerfile que escribía
init hacía `COPY deploy_service` sobre un directorio inexistente y el build
fallaba.
"""

from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

from godml.monitoring_service.logger import get_logger

logger = get_logger()

TEMPLATE_PACKAGE = "godml.templates.deploy_template"
DEPLOY_SERVICE_DIRNAME = "deploy_service"

# Los artefactos de compilación de la plantilla no deben viajar al proyecto
# del usuario ni, después, a la imagen Docker.
_IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


def scaffold_deploy_service(target_dir: str | Path = ".") -> Path:
    """
    Crea `deploy_service/` en `target_dir` a partir de la plantilla del paquete.

    Es idempotente: si el directorio ya existe no lo toca, para no pisar las
    customizaciones del usuario —que es justamente el motivo por el que la
    plantilla se copia en lugar de importarse.
    """
    destination = Path(target_dir) / DEPLOY_SERVICE_DIRNAME

    if destination.exists():
        return destination

    template_root = files(TEMPLATE_PACKAGE)
    logger.info(f"Generando {DEPLOY_SERVICE_DIRNAME}/ desde plantilla...")
    shutil.copytree(str(template_root), str(destination), ignore=_IGNORED)
    return destination
