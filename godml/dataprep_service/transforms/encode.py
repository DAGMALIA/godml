import pandas as pd
from .base import BaseTransform

class OneHot(BaseTransform):
    name = "one_hot"
    def apply(self, df: pd.DataFrame, columns=None, drop_first: bool = False, **_):
        columns = columns or []
        return pd.get_dummies(df, columns=columns, drop_first=drop_first)

class LabelEncode(BaseTransform):
    name = "label_encode"
    def apply(self, df: pd.DataFrame, columns=None, **_):
        columns = columns or []
        out = df.copy()
        for c in columns:
            out[c] = out[c].astype("category").cat.codes
        return out
