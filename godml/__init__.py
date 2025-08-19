# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License
import os
import warnings

# 🔇 Supre logs de TensorFlow antes de importarlo
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

#--------------------------------------------------------------------------------#

from .notebook_api import GodmlNotebook, quick_train, train_from_yaml, quick_train_yaml
from .core_service.parser import load_pipeline
from .core_service.executors import get_executor
from .utils.model_storage import (
    save_model_to_structure, 
    load_model_from_structure,
    list_models,
    promote_model
)

__version__ = "0.4.2"
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
    "promote_model"
]

#print("✅ godml/__init__.py cargado y logs silenciados")