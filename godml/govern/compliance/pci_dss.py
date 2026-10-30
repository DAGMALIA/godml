# Copyright (c) 2024
# SPDX-License-Identifier: MIT

from typing import Iterable

import pandas as pd
from .base_compliance import BaseCompliance
from .pii_detector import PiiDetector
from .compliance_utils import (
    hmac_truncated,
    pii_hash_key,
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
          * 'hash_sensitive'  -> HMAC-SHA256 truncado con la llave GODML_PII_KEY
    """

    def __init__(
        self,
        policy: str = "mask_sensitive",
        hash_len: int = 12,
        exclude_columns: Iterable[str] = (),
    ):
        self.policy = (policy or "mask_sensitive").strip().lower()
        self.hash_len = hash_len
        self.detector = PiiDetector()
        # Never treated as PII, e.g. the training target (F1-07).
        self.exclude_columns = tuple(exclude_columns or ())

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

    def _hash_col(self, series: pd.Series, key: str) -> pd.Series:
        # F1-06: keyed HMAC; a plain SHA-256 of PII can be reversed by brute force.
        return series.apply(lambda v: hmac_truncated(v, key, self.hash_len))

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        # F1-06: the key is required whenever compliance runs, whatever the
        # policy, so a misconfiguration fails before any data is touched.
        key = pii_hash_key()
        if df is None or df.empty:
            return df

        df = df.copy()

        # 1) Detección por contenido (muestra)
        detected_content = self.detector.detect_all(
            df, exclude_columns=self.exclude_columns
        )  # dict: col -> pii_type

        # 2) Detección por nombre (heurística)
        detected_name = {
            col: "name_heuristic"
            for col in df.columns
            if col not in self.exclude_columns and is_pii_column(col)
        }

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
                df[col] = self._hash_col(df[col], key)
            else:
                # Política desconocida => por seguridad, hasheamos
                df[col] = self._hash_col(df[col], key)

        # Ejecuta drops al final para evitar conflictos
        if columns_to_drop:
            df = df.drop(columns=columns_to_drop, errors="ignore")
            print(f"🧹 [PCI-DSS] Columnas eliminadas por política: {columns_to_drop}")

        return df

    def describe(self) -> str:
        return "PCI-DSS Compliance: PII masking/hash/drop with mixed detection (content + name heuristic)."
