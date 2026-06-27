# config_service/loader.py
import yaml
from pathlib import Path
from .schema import PipelineDefinition
from .resolver import resolve_env_variables
from godml.monitoring_service.logger import ConfigurationError, godml_logger

MAX_YAML_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def load_config(path):
    try:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Archivo de configuracion no encontrado: {path}")

        file_size = config_path.stat().st_size
        if file_size > MAX_YAML_SIZE_BYTES:
            raise ConfigurationError(
                f"Archivo YAML demasiado grande ({file_size / 1_048_576:.1f} MB). "
                f"Maximo permitido: {MAX_YAML_SIZE_BYTES // 1_048_576} MB. "
                "Si es un archivo de datos, usa dataset.uri en lugar de embeber datos en el YAML."
            )

        try:
            with open(config_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parseando YAML: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error leyendo archivo: {e}")

        if raw is None:
            raise ConfigurationError("Archivo de configuracion esta vacio")

        try:
            resolved = resolve_env_variables(raw)
        except Exception as e:
            raise ConfigurationError(f"Error resolviendo variables de entorno: {e}")

        try:
            config = PipelineDefinition(**resolved)
            godml_logger.info(f"Configuracion cargada desde {path}")
            return config
        except Exception as e:
            raise ConfigurationError(f"Error creando definicion de pipeline: {e}")

    except (FileNotFoundError, ConfigurationError):
        raise
    except Exception as e:
        raise ConfigurationError(f"Error inesperado cargando configuracion: {e}")
