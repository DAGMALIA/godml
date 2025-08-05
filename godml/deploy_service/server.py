# deploy_service/server.py

from fastapi import FastAPI, Request
from pydantic import BaseModel
import joblib
import pandas as pd
from pathlib import Path
import inspect
from xgboost import DMatrix
import xgboost as xgb

app = FastAPI()
model = None

class InputData(BaseModel):
    data: dict


@app.on_event("startup")
def load_model():

    model_path = Path("models/production/model.pkl")
    if not model_path.exists():
        raise RuntimeError(f"Modelo no encontrado en {model_path}")
    
    app.state.model = joblib.load(model_path)
    print("✅ Modelo cargado correctamente.")



@app.post("/predict")
def predict(input_data: InputData, request: Request):

    model = request.app.state.model
    df = pd.DataFrame([input_data.data])
    print("📥 Input recibido:")
    print(df)

    try:
        sig = inspect.signature(model.predict)
        params = sig.parameters

        if "data" in params or isinstance(model, xgb.Booster):
            print("🔎 Detectado modelo XGBoost nativo (usa DMatrix)")

            expected_features = model.feature_names
            df = df[expected_features]
            dmatrix = xgb.DMatrix(df, feature_names=expected_features)
            prediction = model.predict(dmatrix)
        else:
            print("🔎 Modelo sklearn o pipeline")
            prediction = model.predict(df)

        return {"prediction": prediction.tolist()}

    except Exception as e:
        print("❌ Error al predecir:", str(e))
        raise e
