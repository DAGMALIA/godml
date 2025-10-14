import pandas as pd
from .base import BaseTransform

class StandardScale(BaseTransform):
    name = "standard_scale"
    def apply(self, df: pd.DataFrame, columns=None, **_):
        columns = columns or []
        out = df.copy()
        for c in columns:
            mu = out[c].astype(float).mean()
            sd = out[c].astype(float).std(ddof=0) or 1.0
            out[c] = (out[c].astype(float) - mu) / sd
        return out

class MinMaxScale(BaseTransform):
    name = "minmax_scale"
    def apply(self, df: pd.DataFrame, columns=None, feature_range=(0,1), **_):
        columns = columns or []
        a, b = feature_range
        out = df.copy()
        for c in columns:
            x = out[c].astype(float)
            xmin, xmax = x.min(), x.max()
            denom = (xmax - xmin) if (xmax - xmin) != 0 else 1.0
            out[c] = a + (x - xmin) * (b - a) / denom
        return out
