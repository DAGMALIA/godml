"""
Scikit-learn training script — runs inside a SageMaker SKLearn container.
Supports model_type: random_forest | logistic_regression | lightgbm
"""
import argparse
import glob
import os

import joblib
import pandas as pd
from sklearn.metrics import roc_auc_score


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model_type", type=str, default="random_forest")
    p.add_argument("--n_estimators", type=int, default=100)
    p.add_argument("--max_depth", type=int, default=None)
    p.add_argument("--random_state", type=int, default=42)
    p.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    p.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    return p.parse_args()


def _build_model(args: argparse.Namespace):
    t = args.model_type.lower()
    if t == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            random_state=args.random_state,
        )
    if t == "logistic_regression":
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(max_iter=1000, random_state=args.random_state)
    if t == "lightgbm":
        import lightgbm as lgb
        return lgb.LGBMClassifier(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth or -1,
            random_state=args.random_state,
        )
    raise ValueError(
        f"Unsupported model_type '{t}'. Supported: random_forest, logistic_regression, lightgbm"
    )


def main() -> None:
    args = parse_args()

    files = glob.glob(f"{args.train}/*.csv")
    if not files:
        raise FileNotFoundError(f"No CSV files in {args.train}")
    df = pd.read_csv(files[0])

    target_col = "target" if "target" in df.columns else df.columns[-1]
    X = df.drop(columns=[target_col])
    y = df[target_col]

    model = _build_model(args)
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
