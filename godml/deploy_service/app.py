# godml/deploy_service/app.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Any
from pathlib import Path
import pandas as pd
import joblib

app = FastAPI(title="GODML Model Service")

class PredictionRequest(BaseModel):
    data: List[List[Any]]
    columns: List[str]

def find_latest_model_file(base_dir: Path) -> Path | None:
    """Busca recursivamente el primer archivo que contenga 'model' en su nombre."""
    model_files = list(base_dir.rglob("*model*.pkl")) + list(base_dir.rglob("*model*.joblib"))
    if model_files:
        return model_files[0]  # Puedes ordenar por fecha si prefieres
    return None

# Detectar modelo al iniciar la app
BASE_DIR = Path.cwd()
MODEL_PATH = find_latest_model_file(BASE_DIR / "models")
model = joblib.load(MODEL_PATH) if MODEL_PATH and MODEL_PATH.exists() else None

@app.get("/")
def healthcheck():
    return {
        "status": "ok",
        "message": "GODML Model microservice is running",
        "model_path": str(MODEL_PATH) if model else "Not loaded"
    }

@app.post("/predict")
def predict(req: PredictionRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Modelo no cargado")

    try:
        df = pd.DataFrame(req.data, columns=req.columns)
        predictions = model.predict(df)
        return {"predictions": predictions.tolist()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
