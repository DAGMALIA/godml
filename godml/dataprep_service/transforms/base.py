from abc import ABC, abstractmethod
import pandas as pd

class BaseTransform(ABC):
    name: str

    @abstractmethod
    def apply(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        ...
