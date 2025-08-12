import pandas as pd

def expect_non_null(df: pd.DataFrame, cols):
    for c in cols:
        if df[c].isna().any():
            raise AssertionError(f"Nulls found in {c}")

def expect_unique(df: pd.DataFrame, cols):
    if df.duplicated(subset=cols).any():
        raise AssertionError(f"Duplicates in {cols}")

def expect_range(df: pd.DataFrame, column: str, min=None, max=None):
    if min is not None and (df[column] < min).any():
        raise AssertionError(f"Values < {min} in {column}")
    if max is not None and (df[column] > max).any():
        raise AssertionError(f"Values > {max} in {column}")

def expect_regex(df: pd.DataFrame, column: str, pattern: str):
    ok = df[column].astype("string").str.match(pattern, na=False)
    if (~ok).any():
        raise AssertionError(f"Regex failed in {column}")
