# test_warning_policy.py
"""
Guards the pytest warning policy in pyproject (F0-11): deprecations raised
from godml's own modules fail the test, third-party ones stay warnings.
"""

import warnings

import pytest


def _warn_from(module: str, category: type[Warning]) -> None:
    warnings.warn_explicit(
        "deprecated", category, filename=f"{module}.py", lineno=1, module=module
    )


@pytest.mark.parametrize("module", ["godml", "godml.core.parser"])
@pytest.mark.parametrize("category", [DeprecationWarning, PendingDeprecationWarning])
def test_own_deprecations_are_errors(module, category):
    with pytest.raises(category):
        _warn_from(module, category)


@pytest.mark.parametrize("module", ["sklearn.utils", "godmlextra"])
def test_third_party_deprecations_stay_warnings(module):
    with pytest.warns(DeprecationWarning):
        _warn_from(module, DeprecationWarning)
