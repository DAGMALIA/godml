# compliance_service/pii_detector.py
from __future__ import annotations

import re
import pandas as pd


class PiiDetector:
    """
    Deteccion heuristica de columnas con informacion sensible (PII).
    Detecta 15+ tipos de PII por contenido y nombre de columna.
    """

    # Content-based patterns — ordered from most specific to least
    CONTENT_PATTERNS: dict[str, re.Pattern] = {
        "card_number": re.compile(r"^(?:\d[ -]*?){13,16}$"),
        "email": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$"),
        "ssn": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
        "ssn_compact": re.compile(r"^\d{9}$"),
        "passport": re.compile(r"^[A-Z]{1,2}\d{6,9}$"),
        "phone_us": re.compile(r"^\+?1?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$"),
        "phone_mx": re.compile(r"^\+?52\s?\d{2}\s?\d{4}\s?\d{4}$"),
        "iban": re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}$"),
        "ip_address": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),
        "mac_address": re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$"),
        "zip_code": re.compile(r"^\d{5}(-\d{4})?$"),
        "postal_mx": re.compile(r"^\d{5}$"),
        "cvv": re.compile(r"^\d{3,4}$"),
        "dob": re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}$"),
        "expiration_date": re.compile(r"^(0[1-9]|1[0-2])\/?([0-9]{2})$"),
        "curp": re.compile(r"^[A-Z]{4}\d{6}[HM][A-Z]{5}\d{2}$"),
        "rfc": re.compile(r"^[A-Z]{3,4}\d{6}[A-Z0-9]{3}$"),
        "url": re.compile(r"^https?://[^\s]+$"),
        "coordinates": re.compile(r"^-?\d{1,3}\.\d{4,}$"),
    }

    # Column name heuristics (case-insensitive substring match)
    NAME_HINTS: dict[str, list[str]] = {
        "email": ["email", "correo", "mail"],
        "phone_us": ["phone", "telefono", "tel", "mobile", "celular"],
        "card_number": ["card", "tarjeta", "cc_num", "credit", "debit"],
        "ssn": ["ssn", "social_security", "numero_seguro"],
        "dob": ["dob", "birth", "nacimiento", "fecha_nac", "birthdate"],
        "zip_code": ["zip", "postal", "cp", "codigo_postal"],
        "ip_address": ["ip", "ip_address", "ipaddr", "direccion_ip"],
        "curp": ["curp"],
        "rfc": ["rfc"],
        "passport": ["passport", "pasaporte"],
        "iban": ["iban", "cuenta_bancaria", "bank_account"],
        "coordinates": ["lat", "lon", "latitude", "longitude", "latitud", "longitud"],
    }

    def detect_column_type(self, series: pd.Series, col_name: str = "") -> str:
        """
        Infers PII type from column values and optionally the column name.
        Returns the detected type or 'unknown'.
        """
        col_lower = col_name.lower()

        # Fast-path: column name heuristic
        for pii_type, hints in self.NAME_HINTS.items():
            if any(hint in col_lower for hint in hints):
                return pii_type

        # Content-based detection on a sample
        sample = series.dropna().astype(str).head(20)
        if sample.empty:
            return "unknown"

        for pii_type, pattern in self.CONTENT_PATTERNS.items():
            if all(pattern.match(val.strip()) for val in sample):
                return pii_type

        return "unknown"

    def detect_all(self, df: pd.DataFrame) -> dict[str, str]:
        """
        Detects PII type per column in a DataFrame.
        Returns {column_name: pii_type} for all detected PII columns.
        """
        detected: dict[str, str] = {}
        for col in df.columns:
            pii_type = self.detect_column_type(df[col], col_name=col)
            if pii_type != "unknown":
                detected[col] = pii_type
        return detected
