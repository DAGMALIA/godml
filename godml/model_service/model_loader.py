import os
import importlib.util
from godml.model_service.base_model_interface import BaseModel

def load_custom_model_class(project_path: str, model_type: str, source: str = "local") -> BaseModel:
    class_name = ''.join([part.capitalize() for part in model_type.split('_')]) + "Model"

    if source == "local":
        model_file = os.path.join(project_path, "models", f"{model_type}_model.py")
        if not os.path.isfile(model_file):
            raise FileNotFoundError(f"❌ No se encontró el modelo local en: {model_file}")

        # Carga dinámica local
        spec = importlib.util.spec_from_file_location(class_name, model_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        # Carga desde el core (models_registry)
        module_path = f"model_service.model_registry.{model_type}_model"
        module = importlib.import_module(module_path)

    # Obtener clase del módulo
    model_class = getattr(module, class_name)
    model_instance = model_class()

    if not isinstance(model_instance, BaseModel):
        raise TypeError(f"❌ {class_name} no implementa BaseModel correctamente.")

    return model_instance