"""
Evaluation script — runs inside a SageMaker Processing container (sklearn image).

Loads the trained model and test split, computes metrics, writes evaluation.json.
The PropertyFile in step_builder.py reads this JSON to gate the RegisterModel step.

SageMaker mounts:
  /opt/ml/processing/model/  ← model.tar.gz from TrainingStep
  /opt/ml/processing/test/   ← test split CSV from PreprocessingStep
Output:
  /opt/ml/processing/evaluation/evaluation.json
"""
import glob
import json
import os
import tarfile

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

MODEL_DIR = "/opt/ml/processing/model"
TEST_DIR = "/opt/ml/processing/test"
OUT_DIR = "/opt/ml/processing/evaluation"

os.makedirs(OUT_DIR, exist_ok=True)

target_col = os.environ.get("GODML_TARGET_COL", "target")

# Extract model archive
for archive in glob.glob(f"{MODEL_DIR}/*.tar.gz"):
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(MODEL_DIR)

model_files = glob.glob(f"{MODEL_DIR}/**/*.joblib", recursive=True) + glob.glob(f"{MODEL_DIR}/*.joblib")
if not model_files:
    raise FileNotFoundError(f"No .joblib model found under {MODEL_DIR}")
model = joblib.load(model_files[0])
print(f"Model loaded: {model_files[0]}")

# Load test data
test_files = glob.glob(f"{TEST_DIR}/*.csv")
if not test_files:
    raise FileNotFoundError(f"No CSV found in {TEST_DIR}")
df = pd.read_csv(test_files[0])

if target_col not in df.columns:
    target_col = df.columns[-1]

X_test = df.drop(columns=[target_col])
y_test = df[target_col]

# Compute metrics
try:
    preds_proba = model.predict_proba(X_test)[:, 1]
    preds = (preds_proba >= 0.5).astype(int)
    metrics = {
        "auc": float(roc_auc_score(y_test, preds_proba)),
        "accuracy": float(accuracy_score(y_test, preds)),
        "f1": float(f1_score(y_test, preds, zero_division=0)),
        "precision": float(precision_score(y_test, preds, zero_division=0)),
        "recall": float(recall_score(y_test, preds, zero_division=0)),
    }
except Exception as exc:
    print(f"Warning: binary classification metrics failed ({exc}), falling back to accuracy only")
    preds = model.predict(X_test)
    metrics = {"accuracy": float(accuracy_score(y_test, preds))}

print("Metrics:", json.dumps(metrics, indent=2))

out_path = f"{OUT_DIR}/evaluation.json"
with open(out_path, "w") as f:
    json.dump(metrics, f)
print(f"Saved: {out_path}")
