# core_service/preprocessor.py
# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

from typing import Optional
import pandas as pd
import logging
from godml.dataprep_service.lineage.openlineage_emitter import emit

logger = logging.getLogger(__name__)

class ComplianceEngine:
    """
    Motor centralizado de cumplimiento normativo (v1.0.2+)
    - Aplica PCI-DSS u otras normas definidas.
    - Respeta la política ('mask_sensitive', 'hash_sensitive', 'drop_sensitive').
    - Emite eventos OpenLineage para trazabilidad.
    """

    @staticmethod
    def apply(
        df: pd.DataFrame,
        compliance_type: Optional[str] = None,
        policy: Optional[str] = None
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
            logger.warning("⚠️ [ComplianceEngine] DataFrame vacío. Se omite cumplimiento.")
            return df

        if not compliance_type:
            logger.info("ℹ️ [ComplianceEngine] Sin cumplimiento normativo definido.")
            return df

        compliance_type = str(compliance_type).lower().strip()
        policy = str(policy or "mask_sensitive").lower().strip()

        # 🔒 Compatibilidad con PCI-DSS
        if compliance_type != "pci-dss":
            logger.warning(f"⚠️ [ComplianceEngine] Estándar '{compliance_type}' aún no soportado.")
            return df

        try:
            from godml.compliance_service.pci_dss import PciDssCompliance
        except Exception as e:
            logger.error(f"❌ [ComplianceEngine] Error al importar PCI-DSS: {e}")
            return df

        logger.info(f"🔒 [ComplianceEngine] Aplicando {compliance_type.upper()} con política '{policy}'...")
        try:
            emit("COMPLIANCE_APPLY", {"standard": compliance_type, "policy": policy})
        except Exception as e:
            logger.warning(f"⚠️ [ComplianceEngine] No se pudo emitir evento OpenLineage: {e}")

        try:
            engine = PciDssCompliance(policy=policy)
            df_out = engine.apply(df.copy())
            logger.info(f"✅ [ComplianceEngine] Cumplimiento aplicado correctamente. Columnas finales: {list(df_out.columns)}")
            return df_out
        except Exception as e:
            logger.error(f"❌ [ComplianceEngine] Error durante la aplicación del cumplimiento: {e}")
            return df
