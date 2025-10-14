import pandas as pd

def check_types(df: pd.DataFrame, expected: dict[str, str]):
    for col, typ in expected.items():
        if col not in df.columns:
            raise AssertionError(f"Missing column {col}")
