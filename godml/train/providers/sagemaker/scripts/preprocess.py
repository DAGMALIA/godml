"""
Preprocessing script — runs inside a SageMaker Processing container (sklearn image).

Reads raw data from S3, applies godml compliance when configured (fail-closed),
splits into train/test.

SageMaker mounts:
  Input:   /opt/ml/processing/input/data/   ← raw dataset (from dataset.uri)
  Output:  /opt/ml/processing/output/train/ ← train split CSV
           /opt/ml/processing/output/test/  ← test split CSV

Env vars injected by SageMakerExecutor (via ScriptProcessor.env):
  GODML_TARGET_COL   — target column name (default: "target")
  GODML_COMPLIANCE   — compliance type, e.g. "pci-dss" (optional)
  GODML_POLICY       — compliance policy, e.g. "mask_sensitive" (optional)
"""

import glob
import os

import pandas as pd
from sklearn.model_selection import train_test_split

INPUT_DIR = "/opt/ml/processing/input/data"
OUT_TRAIN = "/opt/ml/processing/output/train"
OUT_TEST = "/opt/ml/processing/output/test"

try:
    from godml.core.dtypes import is_text_like
except ImportError:  # the stock sklearn image does not ship godml

    def is_text_like(dtype) -> bool:
        """Copy of godml.core.dtypes.is_text_like (a parity test keeps them equal)."""
        if isinstance(dtype, pd.CategoricalDtype):
            return False
        return pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(
            dtype
        )


def apply_compliance(
    df: pd.DataFrame, compliance: str, policy: str, target_col: str | None = None
) -> pd.DataFrame:
    """Fail-closed (F1-04): any failure aborts; unprocessed data never reaches training."""
    if not compliance:
        return df
    try:
        from godml.govern.preprocessor import ComplianceEngine
    except ImportError as exc:
        raise RuntimeError(
            f"Compliance '{compliance}' was requested but godml is not installed "
            "in this processing image, so it cannot be applied. Refusing to "
            "continue with unprocessed data."
        ) from exc
    df = ComplianceEngine.apply(  # raises ComplianceError
        df, compliance, policy, exclude_columns=[target_col] if target_col else None
    )
    print(f"Compliance '{compliance}' applied with policy '{policy}'")
    return df


def encode_categoricals(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """Encode text and categorical features (XGBoost/sklearn need numeric input)."""
    df = df.copy()
    for col in df.columns:
        if col == target_col:
            continue
        if is_text_like(df[col].dtype) or isinstance(
            df[col].dtype, pd.CategoricalDtype
        ):
            df[col] = df[col].astype("category").cat.codes
    return df


def main() -> None:
    os.makedirs(OUT_TRAIN, exist_ok=True)
    os.makedirs(OUT_TEST, exist_ok=True)

    target_col = os.environ.get("GODML_TARGET_COL", "target")
    compliance = os.environ.get("GODML_COMPLIANCE", "")
    policy = os.environ.get("GODML_POLICY", "mask_sensitive")

    # Locate input file
    files = (
        glob.glob(f"{INPUT_DIR}/**/*.csv", recursive=True)
        + glob.glob(f"{INPUT_DIR}/*.csv")
        + glob.glob(f"{INPUT_DIR}/**/*.parquet", recursive=True)
        + glob.glob(f"{INPUT_DIR}/*.parquet")
    )
    if not files:
        raise FileNotFoundError(f"No CSV or Parquet file found in {INPUT_DIR}")

    src = files[0]
    print(f"Loading: {src}")
    df = pd.read_csv(src) if src.endswith(".csv") else pd.read_parquet(src)
    print(f"Shape: {df.shape}, columns: {list(df.columns)}")

    df = apply_compliance(df, compliance, policy, target_col)

    # Validate target column
    if target_col not in df.columns:
        raise ValueError(
            f"Target column '{target_col}' not found in dataset. "
            f"Available columns: {list(df.columns)}"
        )

    df = encode_categoricals(df, target_col)

    # Train / test split (stratified when possible)
    X = df.drop(columns=[target_col])
    y = df[target_col]
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

    train_df = X_train.assign(**{target_col: y_train.values})
    test_df = X_test.assign(**{target_col: y_test.values})

    train_df.to_csv(f"{OUT_TRAIN}/train.csv", index=False)
    test_df.to_csv(f"{OUT_TEST}/test.csv", index=False)

    print(f"Train rows: {len(train_df)}  → {OUT_TRAIN}/train.csv")
    print(f"Test  rows: {len(test_df)}   → {OUT_TEST}/test.csv")


if __name__ == "__main__":
    main()
