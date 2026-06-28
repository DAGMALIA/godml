from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional, Union

class Input(BaseModel):
    name: str
    connector: str
    uri: str
    options: Optional[Dict[str, Any]] = None

class Step(BaseModel):
    op: str
    params: Optional[Dict[str, Any]] = None

class Validation(BaseModel):
    type: str
    # Permitir tanto listas (e.g. ["id"]) como dicts (e.g. {"column":"x", "min":0})
    args: Union[Dict[str, Any], List[Any]] = Field(default_factory=dict)

class Output(BaseModel):
    name: str
    connector: str
    uri: str
    options: Optional[Dict[str, Any]] = None

class Recipe(BaseModel):
    inputs: List[Input]
    steps: List[Step] = Field(default_factory=list)
    validations: List[Validation] = Field(default_factory=list)
    outputs: List[Output]

    @field_validator("inputs", "outputs")
    @classmethod
    def not_empty(cls, v):
        if not v:
            raise ValueError("inputs/outputs no pueden estar vacíos")
        return v
