from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, field_validator

VALID_OPS = [
    # I/O
    "csv_read", "csv_write", "parquet_write",
    # Transforms
    "drop_columns", "rename", "select_columns", "drop_duplicates",
    "label_encode", "one_hot", "dropna", "fillna",
    "outlier_flag", "standard_scale", "minmax_scale",
    "lower", "strip", "regex_replace", "cast_types", "lag",
    "select", "safe_cast", "extract_date_parts",
    # Validators
    "expect_non_null", "expect_unique", "expect_range",
    "expect_regex", "check_types",
]


class InputConfig(BaseModel):
    name: str
    connector: Literal["csv", "dataframe", "parquet"]
    uri: Optional[str] = None


class StepConfig(BaseModel):
    op: str
    params: Dict

    @field_validator("op", mode="before")
    @classmethod
    def validate_op(cls, v: str) -> str:
        if v not in VALID_OPS:
            raise ValueError(f"Operacion no soportada en DataPrep: {v}")
        return v


class OutputConfig(BaseModel):
    name: str
    connector: Literal["csv", "dataframe", "parquet"]
    uri: Optional[str] = None


class RecipeSchema(BaseModel):
    inputs: List[InputConfig]
    steps: List[StepConfig]
    outputs: List[OutputConfig]
