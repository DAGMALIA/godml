# MVP: delega a csv/parquet según la extensión. En SaaS real usaremos boto3 y credenciales.
import importlib
import pandas as pd
from typing import Any, Dict

class S3Connector:
    """
    Conector S3 real usando pandas + s3fs.
    Requisitos:
      - pip install s3fs pyarrow (para parquet)
      - Credenciales AWS configuradas (env vars o ~/.aws/credentials)
    """

    def _ensure_s3fs(self):
        if importlib.util.find_spec("s3fs") is None:
            raise RuntimeError(
                "s3fs no está instalado. Instala con: pip install s3fs"
            )

    def _infer_format(self, uri: str, options: Dict[str, Any] | None = None) -> str:
        options = options or {}
        # prioridad: options["format"] -> extensión de archivo
        explicit = options.get("format")
        if explicit in ("csv", "parquet"):
            return explicit
        if uri.lower().endswith(".parquet"):
            return "parquet"
        return "csv"

    def read(self, uri: str, options: Dict[str, Any] | None = None) -> pd.DataFrame:
        self._ensure_s3fs()
        options = options or {}
        fmt = self._infer_format(uri, options)

        # Validaciones rápidas
        if not uri.startswith("s3://"):
            raise ValueError(f"URI no válida para S3: {uri}")

        try:
            if fmt == "parquet":
                # requiere pyarrow
                return pd.read_parquet(uri, **{k: v for k, v in options.items() if k != "format"})
            else:
                return pd.read_csv(uri, **{k: v for k, v in options.items() if k != "format"})
        except Exception as e:
            raise RuntimeError(f"Error leyendo desde S3 ({fmt}): {e}") from e

    def write(self, df: pd.DataFrame, uri: str, options: Dict[str, Any] | None = None) -> None:
        self._ensure_s3fs()
        options = options or {}
        fmt = self._infer_format(uri, options)

        if not uri.startswith("s3://"):
            raise ValueError(f"URI no válida para S3: {uri}")

        try:
            if fmt == "parquet":
                # pandas usará pyarrow si está instalado
                df.to_parquet(uri, index=False, **{k: v for k, v in options.items() if k != "format"})
            else:
                df.to_csv(uri, index=False, **{k: v for k, v in options.items() if k != "format"})
        except Exception as e:
            raise RuntimeError(f"Error escribiendo a S3 ({fmt}): {e}") from e
