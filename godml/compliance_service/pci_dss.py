# Copyright (c) 2024
# Licensed under the MIT License

import pandas as pd
from .base_compliance import BaseCompliance
from .pii_detector import PiiDetector
from .compliance_utils import (
    hash_truncated,
    mask_string,
    mask_email,
    mask_zip_code,
    mask_date,
    is_pii_column,
)

class PciDssCompliance(BaseCompliance):
    """
    PCI-DSS Compliance:
      - Detecta PII por contenido (PiiDetector) y por nombre de columna (heurística).
      - Aplica política configurable:
          * 'drop_sensitive'  -> elimina columnas PII
          * 'mask_sensitive'  -> enmascara (emails, zip, fechas) o mascara genérica
          * 'hash_sensitive'  -> hashing irreversible (sha256 truncado por defecto)
    """

    def __init__(self, policy: str = "mask_sensitive", hash_len: int = 12):
        self.policy = (policy or "mask_sensitive").strip().lower()
        self.hash_len = hash_len
        self.detector = PiiDetector()

    def _mask_col(self, series: pd.Series, pii_type: str) -> pd.Series:
        # Regla específica según tipo
        if pii_type == "email":
            return series.apply(mask_email)
        if pii_type in {"zip_code", "zip"}:
            return series.apply(mask_zip_code)
        if pii_type in {"dob", "expiration_date", "date"}:
            return series.apply(mask_date)
        # Fallback masking genérico
        return series.apply(lambda v: mask_string(str(v), num_prefix=2))

    def _hash_col(self, series: pd.Series) -> pd.Series:
        return series.apply(lambda v: hash_truncated(v, self.hash_len))

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        df = df.copy()

        # 1) Detección por contenido (muestra)
        detected_content = self.detector.detect_all(df)  # dict: col -> pii_type

        # 2) Detección por nombre (heurística)
        detected_name = {col: "name_heuristic" for col in df.columns if is_pii_column(col)}

        # Unimos resultados: preferimos el tipo del detector de contenido
        detected = dict(detected_name, **detected_content)

        if not detected:
            print("🔒 [PCI-DSS] No se detectaron columnas PII.")
            return df

        print(f"🔒 [PCI-DSS] Columnas PII detectadas: {list(detected.keys())}")
        columns_to_drop = []

        for col, content_type in detected.items():
            # Normalizamos tipo: si vino de heurística de nombre, intentamos clasificar
            pii_type = detected_content.get(col, None) or content_type

            if self.policy == "drop_sensitive":
                columns_to_drop.append(col)
            elif self.policy == "mask_sensitive":
                # Si no se pudo clasificar por contenido, aplica máscara genérica
                if pii_type in {None, "unknown", "name_heuristic"}:
                    df[col] = df[col].apply(lambda v: mask_string(str(v), num_prefix=2))
                else:
                    df[col] = self._mask_col(df[col], pii_type)
            elif self.policy == "hash_sensitive":
                df[col] = self._hash_col(df[col])
            else:
                # Política desconocida => por seguridad, hasheamos
                df[col] = self._hash_col(df[col])

        # Ejecuta drops al final para evitar conflictos
        if columns_to_drop:
            df.drop(columns=columns_to_drop, inplace=True, errors="ignore")
            print(f"🧹 [PCI-DSS] Columnas eliminadas por política: {columns_to_drop}")

        return df

    def describe(self) -> str:
        return "PCI-DSS Compliance: PII masking/hash/drop with mixed detection (content + name heuristic)."
