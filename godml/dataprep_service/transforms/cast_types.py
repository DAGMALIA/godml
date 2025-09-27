import pandas as pd
from .base import BaseTransform

def _cast_series(s: pd.Series, target: str):
    if target.startswith("datetime"):
        fmt = None
        if ":" in target:
            fmt = target.split(":", 1)[1]
        return pd.to_datetime(s, errors="coerce", format=fmt)
    if target in ("int", "int64"):
        return pd.to_numeric(s, errors="coerce").astype("Int64")
    if target in ("float", "float64"):
        return pd.to_numeric(s, errors="coerce")
    if target == "str":
        return s.astype("string")
    return s

class CastTypes(BaseTransform):
    name = "cast_types"
    def apply(self, df: pd.DataFrame, mapping=None, **_):
        mapping = mapping or {}
        out = df.copy()
        for col, t in mapping.items():
            if col in out.columns:
                out[col] = _cast_series(out[col], t)
        return out

class SafeCast(CastTypes):
    name = "safe_cast"
