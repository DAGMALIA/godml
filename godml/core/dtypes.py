# utils/dtypes.py
# SPDX-License-Identifier: MIT
"""dtype helpers shared by executors and scripts. Depends only on pandas."""

import pandas as pd


def is_text_like(dtype) -> bool:
    """True for text columns: `object`, or `str`/`string` (pandas 3 default).

    Categoricals are excluded even when their categories are strings; callers
    encode them through their own branch.
    """
    if isinstance(dtype, pd.CategoricalDtype):
        return False
    return pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype)
