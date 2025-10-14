# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from pathlib import Path
import yaml
from godml.config_service.schema import PipelineDefinition
from godml.utils.path_utils import normalize_path
from godml.monitoring_service.logger import SecurityError, ConfigurationError, godml_logger

def _validate_yaml_path(yaml_path: str) -> Path:
    """Valida y normaliza el path del YAML"""
    try:
        path = Path(yaml_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Archivo YAML no encontrado: {yaml_path}")
        if not path.is_file():
            raise ValueError(f"Path no es un archivo: {yaml_path}")
        if path.suffix.lower() not in ['.yml', '.yaml']:
            raise ValueError(f"Archivo debe ser .yml o .yaml: {yaml_path}")
        return path
    except Exception as e:
        raise SecurityError(f"Error validando path YAML: {e}")

def load_pipeline(yaml_path: str) -> PipelineDefinition:
    try:
        # Validar path de forma segura
        validated_path = _validate_yaml_path(yaml_path)
        
        # Cargar YAML de forma segura
        try:
            with open(validated_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parseando YAML: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error leyendo archivo: {e}")

        if content is None:
            raise ConfigurationError("Archivo YAML está vacío")

        # Normalizar rutas si están presentes
        try:
            if "dataset" in content and "uri" in content["dataset"]:
                content["dataset"]["uri"] = normalize_path(content["dataset"]["uri"])

            if "deploy" in content and "batch_output" in content["deploy"]:
                content["deploy"]["batch_output"] = normalize_path(content["deploy"]["batch_output"])
        except Exception as e:
            raise ConfigurationError(f"Error normalizando rutas: {e}")

        # Crear y validar definición del pipeline
        try:
            pipeline_def = PipelineDefinition(**content)
            godml_logger.info(f"✅ Pipeline cargado desde {yaml_path}")
            return pipeline_def
        except Exception as e:
            raise ConfigurationError(f"Error creando definición de pipeline: {e}")
            
    except (SecurityError, ConfigurationError, FileNotFoundError):
        raise
    except Exception as e:
        raise ConfigurationError(f"Error inesperado cargando pipeline: {e}")
