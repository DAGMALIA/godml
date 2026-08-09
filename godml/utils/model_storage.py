# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import joblib
import json
from pathlib import Path
from datetime import datetime
import shutil

def save_model_to_structure(model, model_name: str = None, environment: str = "experiments"):
    """
    Guarda modelo usando pickle en estructura organizada

    Args:
        model: Modelo entrenado a guardar
        model_name: Nombre del modelo (opcional, se genera automáticamente)
        environment: Ambiente donde guardar ("experiments", "staging", "production")

    Returns:
        str: Ruta donde se guardó el modelo
    """
    # Detectar tipo de modelo
    model_type = _detect_model_type(model)

    # Generar nombre si no se proporciona
    if not model_name:
        model_name = f"{model_type}_model"

    # Crear estructura de carpetas
    base_path = Path("models")
    env_path = base_path / environment
    env_path.mkdir(parents=True, exist_ok=True)

    # Generar nombre con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_filename = f"{model_name}_{timestamp}.pkl"
    model_path = env_path / model_filename

    # ✅ Guardar modelo con joblib
    joblib.dump(model, model_path)

    # Crear enlace al más reciente
    latest_path = env_path / f"{model_name}_latest.pkl"
    if latest_path.exists():
        latest_path.unlink()

    # Copiar archivo (compatible con Windows)
    shutil.copy2(model_path, latest_path)

    # Guardar metadatos
    metadata = {
        "model_type": model_type,
        "model_name": model_name,
        "timestamp": timestamp,
        "environment": environment,
        "file_path": str(model_path),
        "format": "pickle"
    }

    metadata_path = env_path / f"{model_name}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Modelo {model_type} guardado: {model_path}")
    return str(model_path)

def load_model_from_structure(model_name: str, environment: str = "production"):
    """
    Carga modelo desde estructura usando pickle

    Args:
        model_name: Nombre del modelo a cargar
        environment: Ambiente desde donde cargar

    Returns:
        Modelo cargado
    """
    model_path = Path("models") / environment / f"{model_name}_latest.pkl"

    if not model_path.exists():
        raise FileNotFoundError(f"Modelo no encontrado: {model_path}")

    # ✅ Cargar con joblib
    model = joblib.load(model_path)

    print(f"Modelo cargado: {model_path}")
    return model

def list_models(environment=None):
    """
    Listar modelos disponibles

    Args:
        environment: Ambiente específico o None para todos

    Returns:
        dict o list: Modelos disponibles
    """
    base_path = Path("models")

    if environment:
        env_path = base_path / environment
        if env_path.exists():
            models = list(env_path.glob("*_latest.pkl"))
            return [m.stem.replace("_latest", "") for m in models]
        return []
    else:
        all_models = {}
        for env in ["production", "staging", "experiments"]:
            env_path = base_path / env
            if env_path.exists():
                models = list(env_path.glob("*_latest.pkl"))
                all_models[env] = [m.stem.replace("_latest", "") for m in models]
            else:
                all_models[env] = []
        return all_models

def promote_model(model_name: str, from_env: str, to_env: str):
    """
    Promover modelo entre ambientes

    Args:
        model_name: Nombre del modelo
        from_env: Ambiente origen
        to_env: Ambiente destino

    Returns:
        str: Ruta del modelo promovido
    """
    from_path = Path("models") / from_env / f"{model_name}_latest.pkl"

    if not from_path.exists():
        raise FileNotFoundError(f"Modelo no encontrado en {from_env}")

    # Cargar y guardar en nuevo ambiente
    model = load_model_from_structure(model_name, from_env)
    new_path = save_model_to_structure(model, model_name, to_env)

    print(f"Modelo promovido de {from_env} a {to_env}")
    return new_path

def _detect_model_type(model):
    """
    Detecta tipo de modelo

    Args:
        model: Modelo a analizar

    Returns:
        str: Tipo de modelo detectado
    """
    model_class = type(model).__name__
    module_name = type(model).__module__

    if "xgboost" in module_name.lower():
        return "xgboost"
    elif "RandomForest" in model_class:
        return "random_forest"
    elif "lightgbm" in module_name.lower():
        return "lightgbm"
    elif "sklearn" in module_name:
        return f"sklearn_{model_class.lower()}"
    elif "tensorflow" in module_name or "keras" in module_name:
        return "tensorflow"
    else:
        return "unknown"
