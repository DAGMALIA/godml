# utils/serving.py
# SPDX-License-Identifier: MIT
"""Inference helpers shared by the deploy server and its scaffold template (F1-11)."""

from __future__ import annotations

import inspect
from typing import Any, Optional

import pandas as pd


class MissingFeaturesError(ValueError):
    """The request lacks features the model was trained with (client error)."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing features: {missing}")


def _is_xgb_booster(model: Any) -> bool:
    try:
        import xgboost as xgb
    except ImportError:
        return False
    if isinstance(model, xgb.Booster):
        return True
    try:
        return "data" in inspect.signature(model.predict).parameters
    except (TypeError, ValueError):
        return False


def expected_features(model: Any) -> Optional[list[str]]:
    """Training feature order: `feature_names_in_` (sklearn, XGBClassifier) or
    `feature_names` (xgboost Booster). None when the model does not record it."""
    names = getattr(model, "feature_names_in_", None)
    if names is None:
        names = getattr(model, "feature_names", None)
    if names is None or len(names) == 0:
        return None
    return [str(n) for n in names]


def align_features(model: Any, df: pd.DataFrame) -> pd.DataFrame:
    """Reorder columns to the training order and drop unknown ones.

    Clients send JSON objects, whose key order is arbitrary; sklearn rejects a
    different column order and a Booster/DMatrix uses position.
    """
    expected = expected_features(model)
    if expected is None:
        return df
    missing = [f for f in expected if f not in df.columns]
    if missing:
        raise MissingFeaturesError(missing)
    return df[expected]


def predict_with_proba(model: Any, df: pd.DataFrame) -> tuple[list, Optional[list]]:
    """Predictions plus class probabilities when the model provides them."""
    if _is_xgb_booster(model):
        import xgboost as xgb

        prediction = model.predict(xgb.DMatrix(df))
        return _to_list(prediction), None

    prediction = model.predict(df)
    probabilities = None
    if hasattr(model, "predict_proba"):
        try:
            probabilities = _to_list(model.predict_proba(df))
        except (AttributeError, NotImplementedError):
            # e.g. SVC(probability=False) exposes predict_proba but cannot use it
            probabilities = None
    return _to_list(prediction), probabilities


def _to_list(values: Any) -> list:
    if hasattr(values, "tolist"):
        return values.tolist()
    if hasattr(values, "__iter__"):
        return list(values)
    return [values]
