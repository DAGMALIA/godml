import re
import importlib
import sys
from pathlib import Path
from typing import Type, Optional
from godml.model_service.base_model_interface import BaseModel
from godml.monitoring_service.logger import SecurityError, ModelLoadError, godml_logger

# Registry estático base
CORE_MODEL_REGISTRY = {
    'random_forest': 'godml.model_service.model_registry.random_forest_model',
    'xgboost': 'godml.model_service.model_registry.xgboost_model',
    'lstm_forecast': 'godml.model_service.model_registry.lstm_forecast_model',
    'linear_regression': 'godml.model_service.model_registry.linear_regression_model',
    'logistic_regression': 'godml.model_service.model_registry.logistic_regression_model'
}

# Registry dinámico para modelos ad-hoc
_adhoc_model_registry = {}

def register_adhoc_model(model_type: str, model_class: Type[BaseModel]) -> None:
    """Registra un modelo ad-hoc de forma segura."""
    if not model_type or not isinstance(model_type, str):
        raise SecurityError("model_type debe ser una cadena no vacía")

    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', model_type):
        raise SecurityError(f"Tipo de modelo inválido: {model_type}")

    if not issubclass(model_class, BaseModel):
        raise SecurityError("La clase debe heredar de BaseModel")

    _adhoc_model_registry[model_type] = model_class
    godml_logger.info(f"✅ Modelo ad-hoc '{model_type}' registrado")

def load_custom_model_class(project_path: str, model_type: str, source: str = "core",
                        adhoc_model_class: Optional[Type[BaseModel]] = None) -> BaseModel:
    """
    Carga un modelo de forma segura.

    Args:
        project_path: Ruta del proyecto
        model_type: Tipo de modelo
        source: 'core', 'adhoc', o 'local'
        adhoc_model_class: Clase del modelo ad-hoc (solo para source='adhoc')
    """
    try:
        # Validar entradas básicas
        if not model_type or not isinstance(model_type, str):
            raise SecurityError("model_type debe ser una cadena no vacía")

        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', model_type):
            raise SecurityError(f"Tipo de modelo inválido: {model_type}")

        if source not in ['core', 'adhoc', 'local']:
            raise SecurityError("source debe ser 'core', 'adhoc' o 'local'")

        if source == "adhoc":
            # Modelo ad-hoc - más seguro
            if adhoc_model_class is not None:
                # Clase pasada directamente
                if not issubclass(adhoc_model_class, BaseModel):
                    raise SecurityError("adhoc_model_class debe heredar de BaseModel")
                model_class = adhoc_model_class
            else:
                # Buscar en registry dinámico
                if model_type not in _adhoc_model_registry:
                    raise ModelLoadError(f"Modelo ad-hoc '{model_type}' no registrado")
                model_class = _adhoc_model_registry[model_type]

            try:
                model_instance = model_class()
            except Exception as e:
                raise ModelLoadError(f"Error instanciando modelo ad-hoc: {e}")

        elif source == "core":
            # Carga desde registry core - seguro
            if model_type not in CORE_MODEL_REGISTRY:
                available = ", ".join(CORE_MODEL_REGISTRY.keys())
                raise SecurityError(f"Modelo core no disponible: {model_type}. Disponibles: {available}")

            try:
                module_path = CORE_MODEL_REGISTRY[model_type]
                module = importlib.import_module(module_path)
                class_name = ''.join([part.capitalize() for part in model_type.split('_')]) + "Model"

                if not hasattr(module, class_name):
                    raise ModelLoadError(f"Clase {class_name} no encontrada")

                model_class = getattr(module, class_name)

                if not issubclass(model_class, BaseModel):
                    raise ModelLoadError(f"{class_name} no hereda de BaseModel")

                model_instance = model_class()

            except ImportError as e:
                raise ModelLoadError(f"Error importando modelo core: {e}")

        else:  # source == "local"
            # Carga local con restricciones estrictas
            if not project_path or not isinstance(project_path, str):
                raise SecurityError("project_path requerido para source='local'")

            # Solo nombres específicos permitidos para local
            allowed_local = {'custom_model', 'user_model', 'project_model'}
            if model_type not in allowed_local:
                allowed = ", ".join(allowed_local)
                raise SecurityError(f"Para local solo se permiten: {allowed}")

            models_dir = Path(project_path) / "models"
            model_file = models_dir / f"{model_type}.py"

            # Validaciones de seguridad estrictas
            try:
                resolved_file = model_file.resolve()
                resolved_base = models_dir.resolve()

                if not str(resolved_file).startswith(str(resolved_base)):
                    raise SecurityError("Path traversal detectado")

                if not resolved_file.suffix == '.py':
                    raise SecurityError("Solo archivos .py permitidos")

                if not resolved_file.is_file():
                    raise FileNotFoundError(f"Archivo no encontrado: {model_file}")

            except Exception as e:
                raise SecurityError(f"Error validando archivo local: {e}")

            # Importación local controlada
            try:
                models_dir_str = str(models_dir)
                path_added = False

                if models_dir_str not in sys.path:
                    sys.path.insert(0, models_dir_str)
                    path_added = True

                try:
                    if model_type in sys.modules:
                        importlib.reload(sys.modules[model_type])
                        module = sys.modules[model_type]
                    else:
                        module = importlib.import_module(model_type)

                    # Buscar clase que herede de BaseModel
                    model_class = None
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            issubclass(attr, BaseModel) and
                            attr != BaseModel):
                            model_class = attr
                            break

                    if model_class is None:
                        raise ModelLoadError("No se encontró clase que herede de BaseModel")

                    model_instance = model_class()

                finally:
                    if path_added and models_dir_str in sys.path:
                        sys.path.remove(models_dir_str)

            except Exception as e:
                raise ModelLoadError(f"Error cargando modelo local: {e}")

        # Validación final
        if not isinstance(model_instance, BaseModel):
            raise TypeError("El modelo no implementa BaseModel correctamente")

        godml_logger.info(f"✅ Modelo {model_type} cargado desde {source}")
        return model_instance

    except (SecurityError, ModelLoadError, FileNotFoundError, TypeError):
        raise
    except Exception as e:
        raise ModelLoadError(f"Error inesperado: {e}")
