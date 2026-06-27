from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd
from joblib import dump, load


def save_artifact(obj: Any, path: str | Path) -> None:
    dump(obj, Path(path))


def load_artifact(path: str | Path) -> Any:
    return load(Path(path))


def emit_lineage(event_type: str, payload: Dict[str, Any]) -> None:
    try:
        from godml.dataprep_service.lineage.openlineage_emitter import emit
        emit(event_type, payload)
    except Exception:
        pass


def summarize_df(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "shape": list(df.shape),
        "nulls": df.isna().sum().to_dict(),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "unique": {c: int(df[c].nunique(dropna=True)) for c in df.columns},
    }


def plot_roc_pr_curves(y_true, y_prob) -> None:
    try:
        from sklearn.metrics import roc_curve, auc, precision_recall_curve, average_precision_score
    except Exception as e:
        raise ImportError("Se requiere scikit-learn para graficar curvas ROC/PR.") from e

    import matplotlib.pyplot as plt

    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)
    plt.figure()
    plt.plot(fpr, tpr, label=f"ROC AUC = {roc_auc:.3f}")
    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.xlabel("FPR")
    plt.ylabel("TPR")
    plt.title("ROC Curve")
    plt.legend(loc="lower right")
    plt.show()

    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    ap = average_precision_score(y_true, y_prob)
    plt.figure()
    plt.plot(recall, precision, label=f"AP = {ap:.3f}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve")
    plt.legend(loc="lower left")
    plt.show()
