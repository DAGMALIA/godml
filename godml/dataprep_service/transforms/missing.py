import pandas as pd
from .base import BaseTransform

class FillNA(BaseTransform):
    name = "fillna"
    def apply(self, df: pd.DataFrame, columns=None, **_):
        columns = columns or {}
        return df.fillna(value=columns)

class DropNA(BaseTransform):
    name = "dropna"
    def apply(self, df: pd.DataFrame, subset=None, how: str = "any", **_):
        return df.dropna(subset=subset, how=how)
