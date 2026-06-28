"""
Preprocessing script — runs inside a SageMaker Processing container (sklearn image).

Reads raw data from S3, applies optional godml compliance, splits into train/test.

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

# Apply compliance if configured
if compliance:
    try:
        from godml.compliance_service.compliance_registry import ComplianceRegistry
        engine = ComplianceRegistry.get(compliance)
        df = engine.apply(df, policy=policy)
        print(f"Compliance '{compliance}' applied with policy '{policy}'")
    except Exception as exc:
        print(f"Warning: compliance step skipped ({exc})")

# Validate target column
if target_col not in df.columns:
    raise ValueError(
        f"Target column '{target_col}' not found in dataset. "
        f"Available columns: {list(df.columns)}"
    )

# Encode remaining categoricals (XGBoost/sklearn need numeric features)
for col in df.select_dtypes(include=["object", "category"]).columns:
    if col != target_col:
        df[col] = df[col].astype("category").cat.codes

# Train / test split (stratified when possible)
X = df.drop(columns=[target_col])
y = df[target_col]
try:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
except ValueError:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

train_df = X_train.assign(**{target_col: y_train.values})
test_df = X_test.assign(**{target_col: y_test.values})

train_df.to_csv(f"{OUT_TRAIN}/train.csv", index=False)
test_df.to_csv(f"{OUT_TEST}/test.csv", index=False)

print(f"Train rows: {len(train_df)}  → {OUT_TRAIN}/train.csv")
print(f"Test  rows: {len(test_df)}   → {OUT_TEST}/test.csv")
