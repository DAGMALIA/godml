import os
import re
from typing import Type, Optional
from godml.model_service.base_model_interface import BaseModel
from godml.monitoring_service.logger import SecurityError, ModelLoadError, godml_logger

# Registry estático completamente seguro - corregido según model_registry.py
CORE_MODEL_REGISTRY = {
    'random_forest': None,
    'xgboost': None,
    'logistic_regression': None,
    'linear_regression': None,
    'lstm_forecast': None
}

# Registry dinámico para modelos ad-hoc
_adhoc_model_registry = {}

def _load_core_model_class(model_type: str) -> Type[BaseModel]:
    """Carga una clase de modelo core de forma completamente segura"""
    try:
        # Mapeo estático y seguro - corregido según model_registry.py
        if model_type == 'random_forest':
            from godml.model_service.model_registry.random_forest_model import RandomForestModel
            return RandomForestModel
        elif model_type == 'xgboost':
            from godml.model_service.model_registry.xgboost_model import XgboostModel
            return XgboostModel
        elif model_type == 'logistic_regression':
            from godml.model_service.model_registry.logistic_regression_model import LogisticRegressionModel
            return LogisticRegressionModel
        elif model_type == 'linear_regression':
            from godml.model_service.model_registry.linear_regression_model import LinearRegressionModel
            return LinearRegressionModel
        elif model_type == 'lstm_forecast':
            from godml.model_service.model_registry.lstm_forecast_model import LSTMForecastModel
            return LSTMForecastModel
        else:
            available = ", ".join(CORE_MODEL_REGISTRY.keys())
            raise ModelLoadError(f"Modelo core no disponible: {model_type}. Disponibles: {available}")
            
    except ImportError as e:
        raise ModelLoadError(f"Error importando modelo core {model_type}: {e}")
    except Exception as e:
        raise ModelLoadError(f"Error inesperado cargando modelo core: {e}")

def register_adhoc_model(model_type: str, model_class: Type[BaseModel]) -> None:
    """Registra un modelo ad-hoc de forma segura."""
    try:
        if not model_type or not isinstance(model_type, str):
            raise SecurityError("model_type debe ser una cadena no vacía")
            
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', model_type):
            raise SecurityError(f"Tipo de modelo inválido: {model_type}")
        
        if not isinstance(model_class, type):
            raise SecurityError("model_class debe ser una clase")
            
        if not issubclass(model_class, BaseModel):
            raise SecurityError("La clase debe heredar de BaseModel")
        
        _adhoc_model_registry[model_type] = model_class
        godml_logger.info(f"✅ Modelo ad-hoc '{model_type}' registrado")
        
    except (SecurityError, TypeError):
        raise
    except Exception as e:
        raise SecurityError(f"Error registrando modelo ad-hoc: {e}")

def load_custom_model_class(project_path: str, model_type: str, source: str = "core", 
                        adhoc_model_class: Optional[Type[BaseModel]] = None) -> BaseModel:
    """
    Carga un modelo de forma completamente segura.
    
    Args:
        project_path: Ruta del proyecto (no usado en versión segura)
        model_type: Tipo de modelo
        source: 'core' o 'adhoc' (local eliminado por seguridad)
        adhoc_model_class: Clase del modelo ad-hoc (solo para source='adhoc')
    """
    try:
        # Validar entradas básicas
        if not model_type or not isinstance(model_type, str):
            raise SecurityError("model_type debe ser una cadena no vacía")
            
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', model_type):
            raise SecurityError(f"Tipo de modelo inválido: {model_type}")
            
        # Solo permitir core y adhoc por seguridad
        if source not in ['core', 'adhoc']:
            raise SecurityError("source debe ser 'core' o 'adhoc' (local deshabilitado por seguridad)")

        if source == "adhoc":
            # Modelo ad-hoc - completamente seguro
            if adhoc_model_class is not None:
                # Clase pasada directamente
                if not isinstance(adhoc_model_class, type):
                    raise SecurityError("adhoc_model_class debe ser una clase")
                if not issubclass(adhoc_model_class, BaseModel):
                    raise SecurityError("adhoc_model_class debe heredar de BaseModel")
                model_class = adhoc_model_class
            else:
                # Buscar en registry dinámico
                if model_type not in _adhoc_model_registry:
                    available = ", ".join(_adhoc_model_registry.keys()) if _adhoc_model_registry else "ninguno"
                    raise ModelLoadError(f"Modelo ad-hoc '{model_type}' no registrado. Disponibles: {available}")
                model_class = _adhoc_model_registry[model_type]
            
            try:
                model_instance = model_class()
            except Exception as e:
                raise ModelLoadError(f"Error instanciando modelo ad-hoc: {e}")
                
        else:  # source == "core"
            # Carga desde registry core - completamente seguro
            if model_type not in CORE_MODEL_REGISTRY:
                available = ", ".join(CORE_MODEL_REGISTRY.keys())
                raise SecurityError(f"Modelo core no disponible: {model_type}. Disponibles: {available}")
            
            try:
                model_class = _load_core_model_class(model_type)
                
                if not issubclass(model_class, BaseModel):
                    raise ModelLoadError(f"Modelo {model_type} no hereda de BaseModel")
                    
                model_instance = model_class()
                
            except (ImportError, ModelLoadError):
                raise
            except Exception as e:
                raise ModelLoadError(f"Error cargando modelo core: {e}")

        # Validación final
        if not isinstance(model_instance, BaseModel):
            raise TypeError("El modelo no implementa BaseModel correctamente")

        godml_logger.info(f"✅ Modelo {model_type} cargado desde {source}")
        return model_instance
        
    except (SecurityError, ModelLoadError, FileNotFoundError, TypeError):
        raise
    except Exception as e:
        raise ModelLoadError(f"Error inesperado: {e}")