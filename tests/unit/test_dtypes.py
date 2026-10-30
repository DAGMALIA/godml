# test_dtypes.py
"""F1-16: one helper decides which columns are text (object, or `str` in pandas 3)."""

import pandas as pd
import pytest

from godml.core.dtypes import is_text_like


@pytest.mark.parametrize(
    "series, expected",
    [
        (pd.Series(["a", "b"], dtype=object), True),
        # pandas 3 infers text as `str`; pandas 2 calls the same dtype "string"
        (pd.Series(["a", "b"], dtype="string"), True),
        (pd.Series(["a", "b"], dtype="category"), False),
        (pd.Series([1, 2]), False),
        (pd.Series([1.5, 2.5]), False),
        (pd.Series([True, False]), False),
        (pd.to_datetime(pd.Series(["2026-01-01"])), False),
    ],
)
def test_is_text_like(series, expected):
    assert is_text_like(series.dtype) is expected
