import pandas as pd
from .base import BaseTransform

class Lag(BaseTransform):
    name = "lag"
    def apply(self, df: pd.DataFrame, column: str, periods: int = 1, new_column: str | None = None, **_):
        out = df.copy()
        out[new_column or f"{column}_lag{periods}"] = out[column].shift(periods)
        return out
