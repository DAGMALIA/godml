# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License
# compliance_service/compliance_utils.py

import hashlib

def hash_sha256(value: str) -> str:
    """
    Aplica hashing SHA-256 a una cadena de texto.
    """
    if not value:
        return ""
    return hashlib.sha256(str(value).encode()).hexdigest()

def mask_string(value: str, num_visible: int = 4, mask_char: str = "*") -> str:
    """
    Enmascara una cadena dejando visibles los últimos `num_visible` caracteres.
    """
    if not value:
        return ""
    value = str(value)
    visible = value[-num_visible:] if num_visible < len(value) else value
    masked = mask_char * max(len(value) - num_visible, 0)
    return masked + visible

def mask_email(email: str) -> str:
    """
    Enmascara un correo dejando la primera letra del nombre y el dominio.
    """
    if not email or "@" not in str(email):
        return ""
    name, domain = str(email).split("@", 1)
    visible = name[:1] if name else ""
    masked = "*" * (len(name) - 1) if len(name) > 1 else ""
    return f"{visible}{masked}@{domain}"

def mask_zip_code(zip_code: str) -> str:
    """
    Enmascara código postal dejando solo los primeros 2 dígitos visibles.
    """
    if not zip_code:
        return ""
    zip_code = str(zip_code)
    return zip_code[:2] + "*" * max(len(zip_code) - 2, 0)

def mask_date(date_str: str) -> str:
    """
    Enmascara completamente una fecha.
    """
    if not date_str:
        return ""
    return "****-**-**"

def is_pii_column(col_name: str) -> bool:
    """
    Detección básica de columnas con datos sensibles (PII) por nombre.
    """
    if not col_name:
        return False
    pii_keywords = ["name", "email", "address", "ssn", "card", "cvv", "zip", "dob"]
    return any(k in col_name.lower() for k in pii_keywords)
