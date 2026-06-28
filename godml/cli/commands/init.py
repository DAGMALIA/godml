from __future__ import annotations

import os
from pathlib import Path

import typer

from godml.monitoring_service.logger import get_logger, SecurityError
from godml.utils.path_utils import sanitize_for_log, validate_safe_path
from godml.utils.yaml_utils import generate_default_yaml, generate_dockerfile_txt, generate_readme_md

logger = get_logger()


def init_command(project_name: str) -> None:
    try:
        if ".." in project_name or os.path.isabs(project_name):
            raise SecurityError("Nombre de proyecto no permitido")

        logger.info(f"Inicializando proyecto GODML: {sanitize_for_log(project_name)}")

        safe_project_name = validate_safe_path(project_name, os.getcwd())
        project_path = Path(safe_project_name)
        project_path.mkdir(exist_ok=True)

        for folder in ["data", "outputs", "models"]:
            folder_path = validate_safe_path(str(project_path / folder))
            Path(folder_path).mkdir(exist_ok=True)

        yaml_path = validate_safe_path(str(project_path / "godml.yml"))
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(generate_default_yaml(project_name))

        readme_path = validate_safe_path(str(project_path / "README.md"))
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(generate_readme_md(project_name))

        dockerfile_path = validate_safe_path(str(project_path / "Dockerfile"))
        if not Path(dockerfile_path).exists():
            with open(dockerfile_path, "w", encoding="utf-8") as f:
                f.write(generate_dockerfile_txt())

        logger.info(f"Proyecto '{sanitize_for_log(project_name)}' creado exitosamente.")
        logger.info(f"Ubicacion: {sanitize_for_log(str(project_path.absolute()))}")
        logger.info(f"Proximos pasos: cd {sanitize_for_log(project_name)} && godml run -f godml.yml")

    except PermissionError as e:
        logger.error(f"Error de permisos: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except OSError as e:
        logger.error(f"Error del sistema: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Error inesperado: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
