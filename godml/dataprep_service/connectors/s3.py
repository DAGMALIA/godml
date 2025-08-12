# MVP: delega a csv/parquet según la extensión. En SaaS real usaremos boto3 y credenciales.
import os
from .csv import CSVConnector
from .parquet import ParquetConnector

EXT_MAP = {".csv": CSVConnector, ".parquet": ParquetConnector}

def pick_connector_by_ext(uri: str):
    _, ext = os.path.splitext(uri.lower())
    if ext not in EXT_MAP:
        raise ValueError(f"Extensión no soportada para s3-like: {ext}")
    return EXT_MAP[ext]()

class S3Connector:
    def read(self, uri: str, options=None):
        c = pick_connector_by_ext(uri)
        return c.read(uri.replace("s3://", ""), options)

    def write(self, df, uri: str, options=None):
        c = pick_connector_by_ext(uri)
        return c.write(df, uri.replace("s3://", ""), options)
