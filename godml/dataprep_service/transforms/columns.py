import pandas as pd
from .base import BaseTransform

class DropColumns(BaseTransform):
    name = "drop_columns"
    def apply(self, df: pd.DataFrame, columns=None, **_):
        return df.drop(columns=columns or [], errors="ignore")

class Rename(BaseTransform):
    name = "rename"
    def apply(self, df: pd.DataFrame, mapping=None, **_):
        return df.rename(columns=mapping or {})

class SelectColumns(BaseTransform):
    name = "select"
    def apply(self, df: pd.DataFrame, columns=None, **_):
        return df[columns] if columns else df
