# godml/advisor_service/schemas.py

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, validator

# ==============================
# Operaciones soportadas en DataPrep
# ==============================

VALID_OPS = [
    # I/O
    "csv_read", "csv_write", "parquet_write",

    # Transforms
    "drop_columns", "rename", "select_columns", "drop_duplicates",
    "label_encode", "one_hot", "dropna", "fillna",
    "outlier_flag", "standard_scale", "minmax_scale",
    "lower", "strip", "regex_replace", "cast_types", "lag",

    # Validators
    "expect_non_null", "expect_unique", "expect_range",
    "expect_regex", "check_types"
]


# ==============================
# Esquemas de receta
# ==============================

class InputConfig(BaseModel):
    name: str
    connector: Literal["csv", "dataframe", "parquet"]
    uri: Optional[str]


class StepConfig(BaseModel):
    op: str
    params: Dict

    @validator("op")
    def validate_op(cls, v):
        if v not in VALID_OPS:
            raise ValueError(f"⚠️ Operación no soportada en DataPrep: {v}")
        return v


class OutputConfig(BaseModel):
    name: str
    connector: Literal["csv", "dataframe", "parquet"]
    uri: Optional[str]


class RecipeSchema(BaseModel):
    """
    Representa una receta de DataPrep.
    """
    inputs: List[InputConfig]
    steps: List[StepConfig]
    outputs: List[OutputConfig]
