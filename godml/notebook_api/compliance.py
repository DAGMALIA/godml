from __future__ import annotations

import pandas as pd


def apply_compliance(df: pd.DataFrame, standard: str = "pci-dss") -> pd.DataFrame:
    std = (standard or "").lower().strip()
    if std != "pci-dss":
        return df
    from godml.compliance_service.pci_dss import PciDssCompliance
    return PciDssCompliance().apply(df.copy())
