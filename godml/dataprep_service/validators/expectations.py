import pandas as pd

def expect_non_null(df: pd.DataFrame, columns):
    """
    Verifica que las columnas no contengan valores nulos.
    Acepta string (columna única) o lista de strings.
    """
    if isinstance(columns, str):
        columns = [columns]
    for col in columns:
        if df[col].isna().any():
            raise ValueError(f"Column {col} has null values")
    return True


def expect_unique(df: pd.DataFrame, columns):
    """
    Verifica que las columnas tengan valores únicos.
    Acepta string (columna única) o lista de strings.
    """
    if isinstance(columns, str):
        columns = [columns]
    for col in columns:
        if not df[col].is_unique:
            raise ValueError(f"Column {col} has duplicate values")
    return True


def expect_range(df: pd.DataFrame, columns, min=None, max=None):
    """
    Verifica que los valores de las columnas estén dentro del rango [min, max].
    Acepta string (columna única) o lista de strings.
    """
    if isinstance(columns, str):
        columns = [columns]
    for col in columns:
        if min is not None and (df[col] < min).any():
            raise ValueError(f"Column {col} has values below {min}")
        if max is not None and (df[col] > max).any():
            raise ValueError(f"Column {col} has values above {max}")
    return True


def expect_regex(df: pd.DataFrame, columns, pattern: str):
    """
    Verifica que los valores de las columnas hagan match con el regex.
    Acepta string (columna única) o lista de strings.
    """
    if isinstance(columns, str):
        columns = [columns]
    for col in columns:
        ok = df[col].astype("string").str.match(pattern, na=False)
        if not ok.all():
            raise ValueError(f"Column {col} has values not matching {pattern}")
    return True
