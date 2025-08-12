import pandas as pd
from .base import BaseTransform

class Join(BaseTransform):
    name = "join"
    def apply(self, df: pd.DataFrame, right: pd.DataFrame = None, on=None, how: str = "inner", **_):
        if right is None:
            raise ValueError("Join requiere 'right' DataFrame")
        return df.merge(right, on=on, how=how)
