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
from pathlib import Path
from typing import Any

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


def _safe_members(tar: tarfile.TarFile, dest: str):
    """Yield members that stay inside `dest` (F1-18).

    `str.startswith` let siblings such as `<dest>_evil/` through; links are
    rejected because a model archive never needs them and they can point out.
    """
    root = Path(dest).resolve()
    for member in tar.getmembers():
        target = (root / member.name).resolve()
        if member.issym() or member.islnk() or not target.is_relative_to(root):
            raise ValueError(f"Unsafe path in tarball: {member.name}")
        yield member


# Python >= 3.12 (and 3.11.4+) ships extraction filters; "data" also rejects
# absolute paths, links out of the destination and special files. Older
# interpreters (some SageMaker images) rely on _safe_members alone.
_EXTRACT_KWARGS: dict[str, Any] = (
    {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
)


def extract_model_archives(model_dir: str) -> None:
    for archive in glob.glob(f"{model_dir}/*.tar.gz"):
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(  # noqa: S202
                model_dir, members=_safe_members(tar, model_dir), **_EXTRACT_KWARGS
            )


def compute_metrics(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    try:
        preds_proba = model.predict_proba(X_test)[:, 1]
        preds = (preds_proba >= 0.5).astype(int)
        return {
            "auc": float(roc_auc_score(y_test, preds_proba)),
            "accuracy": float(accuracy_score(y_test, preds)),
            "f1": float(f1_score(y_test, preds, zero_division=0)),
            "precision": float(precision_score(y_test, preds, zero_division=0)),
            "recall": float(recall_score(y_test, preds, zero_division=0)),
        }
    except Exception as exc:  # noqa: BLE001
        print(
            f"Warning: binary classification metrics failed ({exc}), falling back to accuracy only"
        )
        preds = model.predict(X_test)
        return {"accuracy": float(accuracy_score(y_test, preds))}


def main(
    model_dir: str = MODEL_DIR, test_dir: str = TEST_DIR, out_dir: str = OUT_DIR
) -> None:
    os.makedirs(out_dir, exist_ok=True)
    target_col = os.environ.get("GODML_TARGET_COL", "target")

    # Extract model archive — members are checked against path traversal (B202)
    extract_model_archives(model_dir)

    model_files = glob.glob(f"{model_dir}/**/*.joblib", recursive=True) + glob.glob(
        f"{model_dir}/*.joblib"
    )
    if not model_files:
        raise FileNotFoundError(f"No .joblib model found under {model_dir}")
    model = joblib.load(model_files[0])
    print(f"Model loaded: {model_files[0]}")

    # Load test data
    test_files = glob.glob(f"{test_dir}/*.csv")
    if not test_files:
        raise FileNotFoundError(f"No CSV found in {test_dir}")
    df = pd.read_csv(test_files[0])

    if target_col not in df.columns:
        target_col = df.columns[-1]

    X_test = df.drop(columns=[target_col])
    y_test = df[target_col]

    metrics = compute_metrics(model, X_test, y_test)
    print("Metrics:", json.dumps(metrics, indent=2))

    out_path = f"{out_dir}/evaluation.json"
    with open(out_path, "w") as f:
        json.dump(metrics, f)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
