import pandas as pd
import re
from .base import BaseTransform

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

class RegexReplace(BaseTransform):
    name = "regex_replace"
    def apply(self, df: pd.DataFrame, column: str, pattern: str, repl: str, **_):
        out = df.copy()
        out[column] = out[column].astype("string").str.replace(pattern, repl, regex=True)
        return out
