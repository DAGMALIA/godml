# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import pandas as pd
from .base_compliance import BaseCompliance
from .compliance_utils import (
    hash_sha256,
    mask_string,
    mask_email,
    mask_zip_code,
    mask_date
)


PII_DETECTORS = {
    "card_number": lambda val: isinstance(val, str) and val.isdigit() and 12 <= len(val) <= 19,
    "email": lambda val: isinstance(val, str) and "@" in val and "." in val,
    "cvv": lambda val: isinstance(val, str) and len(val) in (3, 4) and val.isdigit(),
    "expiration_date": lambda val: isinstance(val, str) and any(sep in val for sep in ["/", "-"]),
    "zip_code": lambda val: isinstance(val, str) and val.isdigit() and len(val) in (5, 9),
    "dob": lambda val: isinstance(val, str) and any(sep in val for sep in ["-", "/"]),
    "ssn": lambda val: isinstance(val, str) and len(val) == 11 and val[3] == "-" and val[6] == "-",
    "name": lambda val: isinstance(val, str) and val.istitle() and " " in val,
    "address": lambda val: isinstance(val, str) and any(x in val.lower() for x in ["street", "ave", "blvd", "road", "calle"])
}


PII_MASKERS = {
    "card_number": lambda val: mask_string(val, num_visible=4),
    "email": mask_email,
    "cvv": lambda _: None,
    "expiration_date": lambda _: "MM/YY",
    "name": hash_sha256,
    "address": hash_sha256,
    "zip_code": mask_zip_code,
    "ssn": hash_sha256,
    "dob": mask_date,
}


class PciDssCompliance(BaseCompliance):
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        columns_to_drop = []

        for col in df.columns:
            col_lower = col.lower()

            if "card" in col_lower:
                df[col] = df[col].apply(lambda x: mask_string(x, num_visible=4))
            elif "cvv" in col_lower:
                columns_to_drop.append(col)
            elif "expiration" in col_lower or "exp" in col_lower:
                df[col] = df[col].apply(lambda x: "MM/YY")
            elif "name" in col_lower:
                df[col] = df[col].apply(hash_sha256)
            elif "email" in col_lower:
                df[col] = df[col].apply(mask_email)
            elif "address" in col_lower:
                df[col] = df[col].apply(hash_sha256)
            elif "zip" in col_lower or "postal" in col_lower:
                df[col] = df[col].apply(mask_zip_code)
            elif "ssn" in col_lower:
                df[col] = df[col].apply(hash_sha256)
            elif "dob" in col_lower or "birth" in col_lower:
                df[col] = df[col].apply(mask_date)

        # 🔥 Ejecutar drop fuera del bucle
        if columns_to_drop:
            df.drop(columns=columns_to_drop, inplace=True)

        return df
