# core_service/preprocessor.py
# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT

from typing import Optional, Sequence
import pandas as pd
import logging
from godml.govern.compliance.errors import ComplianceError, unsupported_standard
from godml.observe.lineage.openlineage_emitter import emit

logger = logging.getLogger(__name__)


class ComplianceEngine:
    """
    Motor centralizado de cumplimiento normativo
    - Aplica PCI-DSS u otras normas definidas.
    - Respeta la política ('mask_sensitive', 'hash_sensitive', 'drop_sensitive').
    - Emite eventos OpenLineage para trazabilidad.
    """

    @staticmethod
    def apply(
        df: pd.DataFrame,
        compliance_type: Optional[str] = None,
        policy: Optional[str] = None,
        exclude_columns: Optional[Sequence[str]] = None,
    ) -> pd.DataFrame:
        """
        Aplica el estándar de cumplimiento sobre el DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Dataset de entrada.
        compliance_type : str, opcional
            Estándar (ej. "pci-dss").
        policy : str, opcional
            Política de tratamiento de PII (mask_sensitive, hash_sensitive, drop_sensitive).
        """
        if df is None or df.empty:
            logger.warning(
                "⚠️ [ComplianceEngine] DataFrame vacío. Se omite cumplimiento."
            )
            return df

        if not compliance_type:
            logger.info("ℹ️ [ComplianceEngine] Sin cumplimiento normativo definido.")
            return df

        compliance_type = str(compliance_type).lower().strip()
        policy = str(policy or "mask_sensitive").lower().strip()

        # Fail-closed (F1-01): compliance was requested, so any failure aborts
        # instead of returning the unprocessed DataFrame.
        if compliance_type != "pci-dss":
            raise unsupported_standard(compliance_type)

        try:
            from godml.govern.compliance.pci_dss import PciDssCompliance
        except ImportError as e:
            raise ComplianceError(
                "Compliance 'pci-dss' was requested but its engine could not be imported."
            ) from e

        logger.info(
            f"🔒 [ComplianceEngine] Aplicando {compliance_type.upper()} con política '{policy}'..."
        )
        # Lineage is best-effort observability; it never blocks compliance.
        try:
            emit("COMPLIANCE_APPLY", {"standard": compliance_type, "policy": policy})
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"⚠️ [ComplianceEngine] No se pudo emitir evento OpenLineage: {e}"
            )

        try:
            engine = PciDssCompliance(
                policy=policy, exclude_columns=tuple(exclude_columns or ())
            )
            df_out = engine.apply(df.copy())
        except Exception as e:
            raise ComplianceError(
                f"Compliance '{compliance_type}' (policy '{policy}') failed: {e}"
            ) from e

        logger.info(
            f"✅ [ComplianceEngine] Cumplimiento aplicado correctamente. Columnas finales: {list(df_out.columns)}"
        )
        return df_out
