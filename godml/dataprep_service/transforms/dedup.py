import pandas as pd
from .base import BaseTransform

class DropDuplicates(BaseTransform):
    name = "drop_duplicates"
    def apply(self, df: pd.DataFrame, subset=None, keep: str = "first", **_):
        return df.drop_duplicates(subset=subset, keep=keep)
