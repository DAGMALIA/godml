# compliance_service/compliance_registry.py

from typing import Dict, Type
from godml.compliance_service.base_compliance import BaseCompliance
from godml.compliance_service.pci_dss import PciDssCompliance

class ComplianceRegistry:
    """
    Registro central de normativas de cumplimiento disponibles.
    """

    _registry: Dict[str, Type[BaseCompliance]] = {
        "pci-dss": PciDssCompliance,
    }

    @classmethod
    def get_compliance(cls, compliance_type: str) -> BaseCompliance:
        """
        Retorna una instancia de la clase correspondiente a la normativa solicitada.
        """
        compliance_type = compliance_type.lower()
        if compliance_type not in cls._registry:
            raise ValueError(f"❌ Norma de cumplimiento no registrada: {compliance_type}")
        return cls._registry[compliance_type]()
    
    @classmethod
    def list_supported(cls) -> list:
        """
        Retorna la lista de normativas registradas.
        """
        return list(cls._registry.keys())

    @classmethod
    def register(cls, name: str, compliance_class: Type[BaseCompliance]):
        """
        Permite registrar una nueva norma en tiempo de ejecución.
        """
        cls._registry[name.lower()] = compliance_class
