import pandas as pd
from .base import BaseTransform

class OutlierFlag(BaseTransform):
    name = "outlier_flag"
    def apply(self, df: pd.DataFrame, column: str, method: str = "zscore", threshold: float = 3.0, new_column: str | None = None, **_):
        out = df.copy()
        x = out[column].astype(float)
        if method == "zscore":
            mu = x.mean()
            sd = x.std(ddof=0) or 1.0
            z = (x - mu) / sd
            out[new_column or f"{column}_is_outlier"] = (z.abs() > threshold)
        elif method == "iqr":
            q1, q3 = x.quantile(0.25), x.quantile(0.75)
            iqr = q3 - q1
            lo, hi = q1 - threshold * iqr, q3 + threshold * iqr
            out[new_column or f"{column}_is_outlier"] = (x < lo) | (x > hi)
        else:
            raise ValueError("method debe ser 'zscore' o 'iqr'")
        return out
