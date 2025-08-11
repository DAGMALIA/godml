# config_service/loader.py
import yaml
from pathlib import Path
from .schema import PipelineDefinition
from .resolver import resolve_env_variables
from godml.monitoring_service.logger import ConfigurationError, godml_logger

def load_config(path):
    try:
        # Validar que el archivo existe
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {path}")
        
        # Cargar YAML de forma segura
        try:
            with open(config_path) as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parseando YAML: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error leyendo archivo: {e}")
        
        if raw is None:
            raise ConfigurationError("Archivo de configuración está vacío")
        
        # Resolver variables de entorno
        try:
            resolved = resolve_env_variables(raw)
        except Exception as e:
            raise ConfigurationError(f"Error resolviendo variables de entorno: {e}")
        
        # Crear objeto PipelineDefinition (no Config)
        try:
            config = PipelineDefinition(**resolved)
            godml_logger.info(f"✅ Configuración cargada desde {path}")
            return config
        except Exception as e:
            raise ConfigurationError(f"Error creando definición de pipeline: {e}")
            
    except (FileNotFoundError, ConfigurationError):
        raise
    except Exception as e:
        raise ConfigurationError(f"Error inesperado cargando configuración: {e}")
