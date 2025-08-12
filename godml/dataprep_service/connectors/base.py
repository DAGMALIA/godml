import pandas as pd
from typing import Any, Dict

class BaseConnector:
    def read(self, uri: str, options: Dict[str, Any] | None = None) -> pd.DataFrame:
        raise NotImplementedError

    def write(self, df: pd.DataFrame, uri: str, options: Dict[str, Any] | None = None) -> None:
        raise NotImplementedError
