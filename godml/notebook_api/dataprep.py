from __future__ import annotations

import tempfile
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

try:
    from godml.dataprep_service.recipe_executor import (
        preview_recipe as _preview_recipe,
        run_recipe as _run_recipe,
        validate_recipe as _validate_recipe,
    )
except Exception as e:
    raise ImportError("No se pudo importar godml.dataprep_service.") from e


def dataprep_preview(
    recipe_path: str | Path,
    limit: int = 20,
    governance: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    recipe_path = Path(recipe_path)
    _validate_recipe(recipe_path)
    return _preview_recipe(recipe_path, limit=limit, governance=governance)


def dataprep_run(
    recipe_path: str | Path,
    governance: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    recipe_path = Path(recipe_path)
    _validate_recipe(recipe_path)
    return _run_recipe(recipe_path, mode="run", governance=governance)


def dataprep_run_inline(
    recipe: Dict[str, Any] | Any,
    governance: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    if hasattr(recipe, "model_dump"):
        recipe = recipe.model_dump()
    elif hasattr(recipe, "dict"):
        recipe = recipe.dict()  # pydantic v1 fallback
    payload = {"dataprep": recipe} if isinstance(recipe, dict) and "inputs" in recipe else recipe
    with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False, encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
        tmp = Path(f.name)
    return _run_recipe(tmp, mode="run", governance=governance)
