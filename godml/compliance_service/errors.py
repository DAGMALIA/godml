# compliance_service/errors.py
# SPDX-License-Identifier: MIT
"""Compliance errors. Kept free of import side effects (no logging setup)."""


class ComplianceError(RuntimeError):
    """Compliance was requested but could not be applied.

    Governance is fail-closed: callers must abort instead of continuing with
    unprocessed data. Subclasses RuntimeError because the dataprep hook raised
    RuntimeError before (F1-01); F2-06 moves it under the 2.0 error hierarchy.
    """


SUPPORTED_STANDARDS = ("pci-dss",)


def unsupported_standard(standard: str) -> ComplianceError:
    """Error for a `governance.compliance` value GoDML cannot apply."""
    supported = ", ".join(SUPPORTED_STANDARDS)
    return ComplianceError(
        f"Compliance standard '{standard}' is not supported (supported: {supported}). "
        f"Data processed with this setting was never protected by '{standard}': "
        "GoDML versions before 1.4.0 skipped it silently. "
        "To fix it, set `governance.compliance: pci-dss` or remove the "
        "`compliance` key. See CHANGELOG 1.4.0."
    )
