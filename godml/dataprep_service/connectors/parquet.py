import importlib
import pandas as pd
from .base import BaseConnector

class ParquetConnector(BaseConnector):
    def _ensure_pyarrow(self):
        if importlib.util.find_spec("pyarrow") is None:
            raise RuntimeError("pyarrow no está instalado; requerido para Parquet.")

    def read(self, uri: str, options=None) -> pd.DataFrame:
        self._ensure_pyarrow()
        return pd.read_parquet(uri)

    def write(self, df: pd.DataFrame, uri: str, options=None) -> None:
        self._ensure_pyarrow()
        options = options or {}
        df.to_parquet(uri, index=False)
