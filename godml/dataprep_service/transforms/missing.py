import pandas as pd
from .base import BaseTransform

class FillNA(BaseTransform):
    name = "fillna"

    def apply(self, df: pd.DataFrame, columns=None, value=None, **_):
        if isinstance(columns, str):
            columns = [columns]

        # Si no hay valor explícito, escoger uno por tipo de dato
        if value is None:
            if columns:
                sample_dtype = df[columns[0]].dtype
                if pd.api.types.is_numeric_dtype(sample_dtype):
                    value = 0
                else:
                    value = "MISSING"
            else:
                value = 0

        if columns:
            return df.fillna({c: value for c in columns})
        return df.fillna(value=value)



class DropNA(BaseTransform):
    name = "dropna"

    def apply(self, df: pd.DataFrame, columns=None, **_):
        """
        Elimina filas con valores nulos en las columnas especificadas.
        """
        if isinstance(columns, str):
            columns = [columns]
        return df.dropna(subset=columns)

