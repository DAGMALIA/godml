from __future__ import annotations

import os

import typer

from godml.core_service.parser import load_pipeline
from godml.core_service.executors import get_executor
from godml.monitoring_service.logger import get_logger, SecurityError, ConfigurationError
from godml.utils.path_utils import sanitize_for_log, validate_safe_path

logger = get_logger()


def _normalize_inline_to_full(dataprep: dict, dataset_uri: str) -> dict:
    steps = dataprep.get("steps", []) or []

    if dataset_uri.startswith("s3://"):
        connector = "s3"
    elif dataset_uri.endswith(".parquet"):
        connector = "parquet"
    else:
        connector = "csv"

    read_step = next((s for s in steps if s.get("op") in ("read_csv", "read_parquet")), None)
    write_step = next((s for s in reversed(steps) if s.get("op") in ("write_csv", "write_parquet")), None)

    in_uri = (read_step or {}).get("params", {}).get("path") or dataset_uri
    if write_step and write_step.get("params", {}).get("path"):
        out_uri = write_step["params"]["path"]
    elif connector == "csv":
        out_uri = dataset_uri[:-4] + "_clean.csv"
    elif connector == "parquet":
        out_uri = dataset_uri[:-8] + "_clean.parquet"
    else:
        out_uri = dataset_uri + "_clean"

    core_steps = [s for s in steps if s.get("op") not in ("read_csv", "read_parquet", "write_csv", "write_parquet")]

    return {
        "inputs": [{"name": "raw", "connector": connector, "uri": in_uri}],
        "steps": core_steps,
        "outputs": [{"name": "clean", "connector": connector, "uri": out_uri}],
    }


def run_command(file: str) -> None:
    try:
        if ".." in file:
            raise SecurityError("Ruta no permitida")
        if os.path.isabs(file):
            from godml.cli.validators import _is_safe_absolute_path
            if not _is_safe_absolute_path(file):
                raise SecurityError(f"Ruta absoluta fuera de directorio permitido: {file}")

        yaml_path = validate_safe_path(file)
        print(f"Usando archivo YAML: {yaml_path}")

        pipeline = load_pipeline(str(yaml_path))
        print(f"Dataset: {pipeline.dataset.uri}")
        print(f"Output: {pipeline.deploy.batch_output}")

        if isinstance(pipeline.dataset.dataprep, dict) and "steps" in pipeline.dataset.dataprep and (
            "inputs" not in pipeline.dataset.dataprep or "outputs" not in pipeline.dataset.dataprep
        ):
            pipeline.dataset.dataprep = _normalize_inline_to_full(
                pipeline.dataset.dataprep, pipeline.dataset.uri
            )
            print("dataprep inline normalizado a formato completo.")

        executor = get_executor(pipeline.provider)
        executor.validate(pipeline)
        result = executor.run(pipeline)

        if result is False:
            logger.error("Entrenamiento fallido")
            raise typer.Exit(1)

    except FileNotFoundError as e:
        logger.error(f"Archivo no encontrado: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except ConfigurationError as e:
        logger.error(f"Error de configuración: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Error inesperado: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
