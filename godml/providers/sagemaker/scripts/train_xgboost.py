"""
XGBoost training script — runs inside a SageMaker XGBoost container.

SageMaker passes hyperparameters as CLI args and sets:
  SM_MODEL_DIR    — where to write the saved model
  SM_CHANNEL_TRAIN — where training data is mounted
"""
import argparse
import glob
import os

import joblib
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--max_depth", type=int, default=6)
    p.add_argument("--eta", type=float, default=0.3)
    p.add_argument("--n_estimators", type=int, default=100)
    p.add_argument("--objective", type=str, default="binary:logistic")
    p.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    p.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    files = glob.glob(f"{args.train}/*.csv")
    if not files:
        raise FileNotFoundError(f"No CSV files found in {args.train}")
    df = pd.read_csv(files[0])

    target_col = "target" if "target" in df.columns else df.columns[-1]
    X = df.drop(columns=[target_col])
    y = df[target_col]

    model = xgb.XGBClassifier(
        max_depth=args.max_depth,
        learning_rate=args.eta,
        n_estimators=args.n_estimators,
        objective=args.objective,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    model.fit(X, y)

    try:
        auc = roc_auc_score(y, model.predict_proba(X)[:, 1])
        print(f"Train AUC: {auc:.4f}")
    except Exception:
        pass

    os.makedirs(args.model_dir, exist_ok=True)
    out = os.path.join(args.model_dir, "model.joblib")
    joblib.dump(model, out)
    print(f"Model saved: {out}")


if __name__ == "__main__":
    main()
