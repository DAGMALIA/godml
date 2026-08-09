# deploy_service/server.py
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse, Response
    from fastapi.middleware.cors import CORSMiddleware
except ImportError as _e:
    raise ImportError(
        "El deploy service requiere fastapi. "
        "Instala con: pip install godml[api]"
    ) from _e

try:
    import xgboost as xgb
except ImportError:
    xgb = None  # type: ignore[assignment]

from pydantic import BaseModel
import joblib
import pandas as pd
import inspect
import os
import time
from pathlib import Path
from godml.monitoring_service.logger import godml_logger, SecurityError
from godml.monitoring_service.observability import (
    BASELINE_FILENAME,
    ModelObserver,
    find_baseline,
    render_metrics,
)

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
    model_path = None
    try:
        godml_logger.info(f"🚀 Iniciando carga de modelo en {ENVIRONMENT.upper()}")
        model_path = find_model_file()
        validate_model_path(model_path)
        app.state.model = joblib.load(model_path)
        godml_logger.info(f"✅ Modelo cargado: {model_path}")
    except Exception as e:
        godml_logger.error(f"⚠️ Error al cargar modelo: {e}")
        app.state.model = None  # Permite dry-run (CI/CD)

    # El baseline de drift se busca junto al modelo: `godml run` lo escribe en el
    # mismo directorio que el .pkl, así el par modelo/baseline viaja siempre junto.
    search_dirs = [Path.cwd() / "models" / ENVIRONMENT, Path.cwd() / "models"]
    if model_path is not None:
        search_dirs.insert(0, model_path.parent)
    baseline_path = find_baseline(search_dirs)
    if baseline_path is None:
        godml_logger.info(
            f"ℹ️ Sin {BASELINE_FILENAME}: métricas de servicio activas, drift desactivado"
        )

    app.state.observer = ModelObserver(
        environment=ENVIRONMENT,
        baseline_path=baseline_path,
    )
    app.state.observer.set_model_loaded(app.state.model is not None)

# ==========================================================
# 🧠 ENDPOINT DE INFERENCIA
# ==========================================================
def get_observer(request: Request) -> ModelObserver:
    """Devuelve el observer del proceso, creando uno vacío si el startup no corrió."""
    observer = getattr(request.app.state, "observer", None)
    if observer is None:
        observer = ModelObserver(environment=ENVIRONMENT)
        request.app.state.observer = observer
    return observer


@app.post("/predict")
def predict(input_data: InputData, request: Request):
    start = time.time()
    observer = get_observer(request)
    df = None
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
        observer.record_prediction(
            latency=time.time() - start,
            status="success",
            predictions=result,
            features=df,
        )
        godml_logger.info(f"✅ Predicción en {latency}s -> {result}")
        return {"prediction": result, "latency": latency}

    except HTTPException as e:
        # Un 4xx es error de cliente y un 5xx es del modelo: separarlos evita que
        # payloads mal formados contaminen la tasa de error del modelo en Grafana.
        status = "client_error" if e.status_code < 500 else "error"
        observer.record_prediction(latency=time.time() - start, status=status)
        raise e
    except Exception as e:
        observer.record_prediction(latency=time.time() - start, status="error")
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
# 📊 OBSERVABILIDAD: PROMETHEUS & DRIFT
# ==========================================================
@app.get("/metrics")
def metrics():
    """Endpoint de scrape para Prometheus."""
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)

@app.get("/drift")
def drift(request: Request):
    """Estado del drift en JSON, para inspección sin levantar Grafana."""
    return get_observer(request).snapshot()

# ==========================================================
# 🧩 MANEJO GLOBAL DE ERRORES Y MÉTRICAS
# ==========================================================
def _metric_path(request: Request) -> str:
    """
    Path normalizado para usar como label.

    Se usa el patrón de la ruta (`/items/{id}`) y no la URL concreta; las rutas
    sin match colapsan en "unmatched" para que un escaneo de 404s no explote la
    cardinalidad de la TSDB.
    """
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"

@app.middleware("http")
async def timing_and_logging(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
        duration = round(time.time() - start, 4)
        response.headers["X-Response-Time"] = str(duration)
        if IS_DEV:
            godml_logger.info(f"📡 {request.method} {request.url.path} - {duration}s")
        status = response.status_code
    except Exception as exc:
        duration = time.time() - start
        godml_logger.error(f"🔥 Error inesperado: {exc}")
        response = JSONResponse(status_code=500, content={"detail": str(exc)})
        status = 500

    path = _metric_path(request)
    # El propio scrape no se contabiliza: inflaría el RPS con tráfico interno.
    if path != "/metrics":
        get_observer(request).record_http(request.method, path, status, time.time() - start)
    return response

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
