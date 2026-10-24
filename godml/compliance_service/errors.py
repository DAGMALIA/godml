# compliance_service/errors.py
# SPDX-License-Identifier: MIT
"""Compliance errors. Kept free of import side effects (no logging setup)."""


class ComplianceError(RuntimeError):
    """Compliance was requested but could not be applied.

    Governance is fail-closed: callers must abort instead of continuing with
    unprocessed data. Subclasses RuntimeError because the dataprep hook raised
    RuntimeError before (F1-01); F2-06 moves it under the 2.0 error hierarchy.
    """
