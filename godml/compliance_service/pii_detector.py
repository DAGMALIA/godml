# compliance_service/pii_detector.py

import pandas as pd
import re

class PiiDetector:
    """
    Detección heurística de columnas con información sensible (PII) basada en contenido.
    """

    def __init__(self):
        # Expresiones regulares para distintos tipos de PII
        self.patterns = {
            "card_number": re.compile(r"^(?:\d[ -]*?){13,16}$"),  # Visa/Mastercard/etc.
            "email": re.compile(r"^[^@]+@[^@]+\.[^@]+$"),
            "ssn": re.compile(r"^\d{3}-\d{2}-\d{4}$"),  # US SSN
            "zip_code": re.compile(r"^\d{5}(-\d{4})?$"),
            "cvv": re.compile(r"^\d{3,4}$"),
            "dob": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
            "expiration_date": re.compile(r"^(0[1-9]|1[0-2])\/?([0-9]{2})$"),
        }

    def detect_column_type(self, series: pd.Series) -> str:
        """
        Intenta inferir el tipo de PII de una columna basándose en sus valores.
        Retorna el tipo detectado o 'unknown'.
        """
        sample = series.dropna().astype(str).head(10)

        for pii_type, pattern in self.patterns.items():
            if all(pattern.match(str(val)) for val in sample):
                return pii_type

        return "unknown"

    def detect_all(self, df: pd.DataFrame) -> dict:
        """
        Detecta el tipo de PII por columna en un DataFrame.
        Retorna un diccionario: columna → tipo_detectado
        """
        detected = {}
        for col in df.columns:
            pii_type = self.detect_column_type(df[col])
            if pii_type != "unknown":
                detected[col] = pii_type

        return detected
