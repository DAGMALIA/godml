# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License
import os
import warnings

# 🔇 Suprime logs de TensorFlow antes de importarlo
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

__version__ = "0.4.9"

__all__ = [
    "GodmlNotebook", 
    "quick_train", 
    "train_from_yaml", 
    "quick_train_yaml",
    "load_pipeline", 
    "get_executor",
    "save_model_to_structure",
    "load_model_from_structure", 
    "list_models",
    "promote_model",
]

# 🚀 Lazy import: solo se cargan los módulos pesados si alguien realmente los usa
def __getattr__(name):
    if name in {"GodmlNotebook", "quick_train", "train_from_yaml", "quick_train_yaml"}:
        from . import notebook_api
        return getattr(notebook_api, name)

    if name in {"load_pipeline"}:
        from .core_service import parser
        return parser.load_pipeline

    if name in {"get_executor"}:
        from .core_service import executors
        return executors.get_executor

    if name in {"save_model_to_structure", "load_model_from_structure", "list_models", "promote_model"}:
        from .utils import model_storage
        return getattr(model_storage, name)

    raise AttributeError(f"module {__name__} has no attribute {name}")


#print("✅ godml/__init__.py cargado y logs silenciados")