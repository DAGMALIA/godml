# deploy_service/server.py

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
from pathlib import Path
import inspect
import os
import xgboost as xgb
from xgboost import DMatrix
from godml.monitoring_service.logger import godml_logger, SecurityError

app = FastAPI()

class InputData(BaseModel):
    data: dict

def find_model_file() -> Path:
    """
    Busca el archivo de modelo en el directorio correcto del proyecto.
    """
    try:
        # Buscar desde el directorio de trabajo actual
        current_dir = Path.cwd()
        
        # Obtener ambiente desde variable de entorno
        environment = os.getenv("GODML_ENV", "dev")
        
        # Buscar solo en el ambiente especificado
        search_paths = [
            current_dir / "models" / environment,  # Ambiente específico
            current_dir / "models"                 # Fallback general
        ]
        
        godml_logger.info(f"🔍 Buscando modelo para ambiente '{environment}' desde: {current_dir}")
        
        for search_path in search_paths:
            if search_path.exists():
                godml_logger.info(f"📂 Revisando directorio: {search_path}")
                
                # Buscar archivos de modelo
                model_patterns = ["*.pkl", "*model*", "*.joblib", "*.pickle"]
                
                for pattern in model_patterns:
                    for model_file in search_path.glob(pattern):
                        if model_file.is_file():
                            godml_logger.info(f"📦 Modelo encontrado: {model_file}")
                            return model_file
        
        # Si no encuentra nada, mostrar información de debug
        godml_logger.error("❌ No se encontró modelo en ninguna ubicación")
        godml_logger.error("📍 Directorio actual: {current_dir}")
        godml_logger.error("📂 Directorios buscados:")
        for path in search_paths:
            exists = "✅" if path.exists() else "❌"
            godml_logger.error(f"   {exists} {path}")
            
        raise FileNotFoundError("No se encontró ningún archivo de modelo")
        
    except Exception as e:
        godml_logger.error(f"❌ Error buscando modelo: {e}")
        raise

def validate_model_path(model_path: Path) -> None:
    """Valida que el path del modelo sea seguro"""
    try:
        resolved_path = model_path.resolve()
        current_dir = Path.cwd().resolve()
        
        # Verificar que el modelo esté en el directorio del proyecto
        if not str(resolved_path).startswith(str(current_dir)):
            raise SecurityError("El modelo debe estar en el directorio del proyecto")
            
        if not resolved_path.exists():
            raise FileNotFoundError(f"Archivo de modelo no existe: {resolved_path}")
            
        if not resolved_path.is_file():
            raise ValueError(f"Path no es un archivo: {resolved_path}")
            
    except Exception as e:
        raise SecurityError(f"Error validando path del modelo: {e}")

@app.on_event("startup")
def load_model():
    try:
        godml_logger.info("🚀 Iniciando carga del modelo...")
        
        # Buscar modelo
        model_path = find_model_file()
        
        # Validar seguridad del path
        validate_model_path(model_path)
        
        # Cargar modelo
        try:
            app.state.model = joblib.load(model_path)
            godml_logger.info(f"✅ Modelo cargado correctamente desde: {model_path}")
        except Exception as e:
            godml_logger.error(f"❌ Error cargando archivo del modelo: {e}")
            raise RuntimeError(f"Error cargando modelo: {e}")
            
    except Exception as e:
        godml_logger.error(f"❌ Error en startup del servidor: {e}")
        raise RuntimeError(str(e))

@app.post("/predict")
def predict(input_data: InputData, request: Request):
    try:
        # Validar que el modelo esté cargado
        if not hasattr(request.app.state, 'model') or request.app.state.model is None:
            raise HTTPException(status_code=500, detail="Modelo no cargado")
            
        model = request.app.state.model
        
        # Validar entrada
        if not input_data.data:
            raise HTTPException(status_code=400, detail="Datos de entrada vacíos")
            
        df = pd.DataFrame([input_data.data])
        godml_logger.info("📥 Input recibido:")
        godml_logger.info(str(df))

        try:
            # Detectar tipo de modelo y predecir
            sig = inspect.signature(model.predict)
            params = sig.parameters

            if "data" in params or isinstance(model, xgb.Booster):
                godml_logger.info("🔎 Detectado modelo XGBoost nativo (usa DMatrix)")
                
                if hasattr(model, 'feature_names') and model.feature_names:
                    expected_features = model.feature_names
                    df = df[expected_features]
                    
                dmatrix = xgb.DMatrix(df)
                prediction = model.predict(dmatrix)
            else:
                godml_logger.info("🔎 Modelo sklearn o pipeline")
                prediction = model.predict(df)

            # Convertir predicción a formato serializable
            if hasattr(prediction, 'tolist'):
                prediction_result = prediction.tolist()
            else:
                prediction_result = list(prediction) if hasattr(prediction, '__iter__') else [prediction]

            return {"prediction": prediction_result}

        except Exception as e:
            godml_logger.error(f"❌ Error durante predicción: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error en predicción: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        godml_logger.error(f"❌ Error inesperado en predict: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/health")
def health_check():
    """Endpoint de salud del servicio"""
    try:
        model_loaded = hasattr(app.state, 'model') and app.state.model is not None
        return {
            "status": "healthy" if model_loaded else "unhealthy",
            "model_loaded": model_loaded,
            "working_directory": str(Path.cwd())
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
