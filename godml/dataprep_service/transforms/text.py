import pandas as pd
import re
from .base import BaseTransform

try:
    # Primero intenta import relativo
    from . import regex_replace
    cy_regex_replace = regex_replace.cy_regex_replace
    CYTHON_AVAILABLE = True
except ImportError:
    try:
        # Si falla, intenta import absoluto
        import regex_replace
        cy_regex_replace = regex_replace.cy_regex_replace
        CYTHON_AVAILABLE = True
    except ImportError:
        CYTHON_AVAILABLE = False


class Lower(BaseTransform):
    name = "lower"
    def apply(self, df: pd.DataFrame, column: str, **_):
        out = df.copy()
        out[column] = out[column].astype("string").str.lower()
        return out

class Strip(BaseTransform):
    name = "strip"
    def apply(self, df: pd.DataFrame, column: str, **_):
        out = df.copy()
        out[column] = out[column].astype("string").str.strip()
        return out

class RegexReplace:
    name = "regex_replace"

    def apply(self, df: pd.DataFrame, column: str, pattern: str, repl: str, **_):
        if CYTHON_AVAILABLE:
            print("🚀 Usando versión Cython")
            df[column] = cy_regex_replace(df[column].tolist(), pattern, repl)
        else:
            print("🐍 Usando fallback Pandas")
            df[column] = df[column].astype("string").str.replace(pattern, repl, regex=True)
        return df

