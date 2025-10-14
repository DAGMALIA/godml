import pandas as pd
from .base import BaseConnector

class CSVConnector(BaseConnector):
    def read(self, uri: str, options=None) -> pd.DataFrame:
        options = options or {}
        return pd.read_csv(uri, **{k:v for k,v in options.items() if k != "partition_by"})

    def write(self, df: pd.DataFrame, uri: str, options=None) -> None:
        options = options or {}
        df.to_csv(uri, index=False)
