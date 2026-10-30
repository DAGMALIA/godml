# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""GoDML spec v2 (`apiVersion: godml.io/v2`, F2-02).

Every model forbids unknown keys, so a typo is an error instead of a
silently ignored setting. `${VAR}` placeholders are kept as text here; the
loader resolves them (F2-03).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

API_VERSION = "godml.io/v2"
KIND = "ModelPipeline"

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_THRESHOLD = re.compile(r"^(>=|<=|==|>|<)\s*-?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$")

Gate = Literal["pre-train", "post-train", "pre-deploy"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Metadata(_Strict):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    owner: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class Data(_Strict):
    uri: str = Field(min_length=1)
    sha256: str = Field(
        default="auto",
        description="'auto' or the 64-hex SHA-256 of the dataset",
    )
    target: str = Field(min_length=1)

    @field_validator("sha256")
    @classmethod
    def _sha256(cls, value: str) -> str:
        if value != "auto" and not _SHA256.match(value):
            raise ValueError("sha256 must be 'auto' or a 64-character hex digest")
        return value.lower() if value != "auto" else value


class RecipeRef(_Strict):
    recipe: str = Field(min_length=1, description="path to a dataprep recipe")


class Train(_Strict):
    estimator: str = Field(
        min_length=1,
        description="import path (xgboost.XGBClassifier) or catalog alias (xgboost)",
    )
    params: dict[str, Any] = Field(default_factory=dict)
    preprocess: RecipeRef | None = None


class Model(_Strict):
    """Bring your own model: an artifact trained elsewhere."""

    artifact: str = Field(min_length=1)
    preprocess: str | None = None
    postprocess: str | None = None


class Govern(_Strict):
    policies: list[str] = Field(default_factory=list)
    metrics: dict[str, str] = Field(
        default_factory=dict,
        description="metric name -> threshold such as '>= 0.80'",
    )
    gates: list[Gate] = Field(default_factory=list)

    @field_validator("metrics")
    @classmethod
    def _thresholds(cls, value: dict[str, str]) -> dict[str, str]:
        for name, threshold in value.items():
            if not _THRESHOLD.match(threshold.strip()):
                raise ValueError(
                    f"metric '{name}': threshold '{threshold}' must look like "
                    "'>= 0.80' (operators: >=, <=, ==, >, <)"
                )
        return value

    @field_validator("policies", "gates")
    @classmethod
    def _unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("entries must be unique")
        return value


class Variant(_Strict):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    weight: int = Field(ge=0, le=100)


class Serve(_Strict):
    variants: list[Variant] = Field(default_factory=list)

    @field_validator("variants")
    @classmethod
    def _variants(cls, value: list[Variant]) -> list[Variant]:
        names = [v.name for v in value]
        if len(set(names)) != len(names):
            raise ValueError("variant names must be unique")
        if value and sum(v.weight for v in value) != 100:
            raise ValueError("variant weights must add up to 100")
        return value


class Drift(_Strict):
    method: Literal["psi"] = "psi"
    threshold: float = Field(gt=0)


class Observe(_Strict):
    drift: Drift | None = None
    lineage: Literal["openlineage"] | None = None


class Spec(_Strict):
    data: Data
    train: Train | None = None
    model: Model | None = None
    govern: Govern = Field(default_factory=Govern)
    serve: Serve | None = None
    observe: Observe | None = None

    @model_validator(mode="after")
    def _train_or_model(self) -> Spec:
        if (self.train is None) == (self.model is None):
            raise ValueError(
                "set exactly one of 'train' (GoDML trains the model) or "
                "'model' (bring your own model)"
            )
        return self


class PipelineSpecV2(_Strict):
    """A `godml.yml` in spec v2."""

    api_version: Literal["godml.io/v2"] = Field(alias="apiVersion")
    kind: Literal["ModelPipeline"]
    metadata: Metadata
    spec: Spec

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def json_schema() -> dict[str, Any]:
    """JSON Schema of spec v2 (published as schemas/godml-v2.json)."""
    schema = PipelineSpecV2.model_json_schema(by_alias=True)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = (
        "https://raw.githubusercontent.com/DAGMALIA/godml/main/schemas/godml-v2.json"
    )
    return schema


def write_json_schema(path: Path) -> None:
    path.write_text(json.dumps(json_schema(), indent=2) + "\n", encoding="utf-8")
