# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
import pandas as pd


class BaseCompliance(ABC):
    """
    Interfaz base para implementar normativas de cumplimiento como PCI-DSS, HIPAA, GDPR, etc.
    """

    @abstractmethod
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica reglas de cumplimiento sobre un DataFrame.
        """
        pass

    def describe(self) -> str:
        """
        Devuelve una descripción textual de la normativa.
        """
        return self.__class__.__name__
