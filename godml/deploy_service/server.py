# deploy_service/server.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib, pandas as pd, inspect, os, time, json, xgboost as xgb
from pathlib import Path
from godml.monitoring_service.logger import godml_logger, SecurityError

# ==========================================================
# 🌎 ENTORNO ACTUAL
# ==========================================================
ENVIRONMENT = os.getenv("GODML_ENV", "dev").lower()
IS_DEV = ENVIRONMENT in ("dev", "qa")

# ==========================================================
# ⚙️ CONFIGURACIÓN FASTAPI
# ==========================================================
app = FastAPI(
    title=f"GODML Model API ({ENVIRONMENT})",
    version="1.1.0",
    description="Microservicio de inferencia robusto para GODML",
)

# CORS solo en entornos de desarrollo
if IS_DEV:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ==========================================================
# 📦 MODEL UTILITIES
# ==========================================================
class InputData(BaseModel):
    data: dict

def find_model_file() -> Path:
    """Busca el archivo del modelo para el entorno actual"""
    current_dir = Path.cwd()
    search_paths = [current_dir / "models" / ENVIRONMENT, current_dir / "models"]
    for path in search_paths:
        if not path.exists():
            continue
        for pattern in ["*.pkl", "*.joblib", "*.model", "*.pickle"]:
            for model_file in path.glob(pattern):
                return model_file
    raise FileNotFoundError(f"No se encontró modelo para {ENVIRONMENT}")

def validate_model_path(model_path: Path) -> None:
    resolved = model_path.resolve()
    base = Path.cwd().resolve()
    if not str(resolved).startswith(str(base)):
        raise SecurityError("Ruta del modelo fuera del proyecto")
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"Archivo de modelo inválido: {resolved}")

# ==========================================================
# ⚡ CARGA DE MODELO
# ==========================================================
@app.on_event("startup")
def load_model():
    try:
        godml_logger.info(f"🚀 Iniciando carga de modelo en {ENVIRONMENT.upper()}")
        model_path = find_model_file()
        validate_model_path(model_path)
        app.state.model = joblib.load(model_path)
        godml_logger.info(f"✅ Modelo cargado: {model_path}")
    except Exception as e:
        godml_logger.error(f"⚠️ Error al cargar modelo: {e}")
        app.state.model = None  # Permite dry-run (CI/CD)

# ==========================================================
# 🧠 ENDPOINT DE INFERENCIA
# ==========================================================
@app.post("/predict")
def predict(input_data: InputData, request: Request):
    start = time.time()
    try:
        model = getattr(request.app.state, "model", None)
        if model is None:
            raise HTTPException(status_code=500, detail="Modelo no cargado")

        df = pd.DataFrame([input_data.data])

        expected_features = getattr(model, "feature_names", None)
        if expected_features:
            missing = [f for f in expected_features if f not in df.columns]
            if missing:
                raise HTTPException(status_code=400, detail=f"Faltan columnas: {missing}")

        sig = inspect.signature(model.predict)
        if "data" in sig.parameters or isinstance(model, xgb.Booster):
            dmatrix = xgb.DMatrix(df)
            prediction = model.predict(dmatrix)
        else:
            prediction = model.predict(df)

        result = prediction.tolist() if hasattr(prediction, "tolist") else [float(prediction)]
        latency = round(time.time() - start, 4)
        godml_logger.info(f"✅ Predicción en {latency}s -> {result}")
        return {"prediction": result, "latency": latency}

    except HTTPException as e:
        raise e
    except Exception as e:
        godml_logger.error(f"❌ Error en predict: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================================
# ❤️ HEALTH, METADATA & VERSION
# ==========================================================
@app.get("/health")
def health_check():
    model_loaded = getattr(app.state, "model", None) is not None
    return {
        "status": "healthy" if model_loaded else "degraded",
        "environment": ENVIRONMENT,
        "model_loaded": model_loaded,
    }

@app.get("/metadata")
def metadata():
    model = getattr(app.state, "model", None)
    features = getattr(model, "feature_names", [])
    return {"status": "ok", "environment": ENVIRONMENT, "features": features}

@app.get("/version")
def version():
    return {
        "godml_version": os.getenv("GODML_VERSION", "dev"),
        "service_version": "1.1.0",
        "environment": ENVIRONMENT,
    }

# ==========================================================
# 🧩 MANEJO GLOBAL DE ERRORES Y MÉTRICAS
# ==========================================================
@app.middleware("http")
async def timing_and_logging(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
        duration = round(time.time() - start, 4)
        response.headers["X-Response-Time"] = str(duration)
        if IS_DEV:
            godml_logger.info(f"📡 {request.method} {request.url.path} - {duration}s")
        return response
    except Exception as exc:
        godml_logger.error(f"🔥 Error inesperado: {exc}")
        return JSONResponse(status_code=500, content={"detail": str(exc)})

# ==========================================================
# 🧰 ENDPOINT SOLO DEV: /debug/config
# ==========================================================
if IS_DEV:
    @app.get("/debug/config")
    def debug_config():
        """Dev-only endpoint para validar entorno"""
        return {
            "environment": ENVIRONMENT,
            "cwd": str(Path.cwd()),
            "model_loaded": getattr(app.state, "model", None) is not None,
        }
