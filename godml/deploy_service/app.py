# godml/deploy_service/app.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Any
import pandas as pd
import joblib
import os

app = FastAPI(title="GODML Model Service")

MODEL_PATH = "models/production/model.pkl"

# Cargar modelo al iniciar
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = None

class PredictionRequest(BaseModel):
    data: List[List[Any]]  # matriz tipo pandas
    columns: List[str]

@app.get("/")
def healthcheck():
    return {"status": "ok", "message": "GODML Model microservice is running"}

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
