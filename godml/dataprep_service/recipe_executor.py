# godml/dataprep_service/recipe_executor.py

import pandas as pd
from pathlib import Path
from typing import Any, Dict, Optional
from yaml import safe_load

from .schema import Recipe
from .lineage.openlineage_emitter import emit
from .connectors.csv import CSVConnector
from .connectors.parquet import ParquetConnector
from .connectors.s3 import S3Connector

# Transforms
from .transforms.columns import DropColumns, Rename, SelectColumns
from .transforms.types import SafeCast, CastTypes
from .transforms.missing import FillNA, DropNA
from .transforms.encode import OneHot, LabelEncode
from .transforms.scale import StandardScale, MinMaxScale
from .transforms.text import Lower, Strip, RegexReplace
from .transforms.dedup import DropDuplicates
from .transforms.quality import OutlierFlag

TRANSFORMS = {
    "drop_columns": DropColumns(),
    "rename": Rename(),
    "select": SelectColumns(),
    "cast_types": CastTypes(),
    "safe_cast": SafeCast(),
    "fillna": FillNA(),
    "dropna": DropNA(),
    "one_hot": OneHot(),
    "label_encode": LabelEncode(),
    "standard_scale": StandardScale(),
    "minmax_scale": MinMaxScale(),
    "lower": Lower(),
    "strip": Strip(),
    "regex_replace": RegexReplace(),
    "drop_duplicates": DropDuplicates(),
    "outlier_flag": OutlierFlag(),
}

CONNECTORS = {
    "csv": CSVConnector(),
    "parquet": ParquetConnector(),
    "s3": S3Connector(),  # delega por extensión (MVP)
}

from .validators.expectations import (
    expect_non_null, expect_unique, expect_range, expect_regex
)

VALIDATIONS = {
    "expect_non_null": lambda df, args: expect_non_null(df, args),
    "expect_unique":   lambda df, args: expect_unique(df, args),
    "expect_range":    lambda df, args: expect_range(df, **args),
    "expect_regex":    lambda df, args: expect_regex(df, **args),
}

# ---------------------------
# Utilidades internas
# ---------------------------

def _read_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return safe_load(f)

def validate_recipe(file: str | Path) -> Recipe:
    data = _read_yaml(file)
    return Recipe(**data.get("dataprep", data))  # permite raíz o key 'dataprep'

def _read_input(inp) -> pd.DataFrame:
    conn = CONNECTORS[inp.connector]
    emit("READ", {"dataset": inp.uri, "connector": inp.connector})
    return conn.read(inp.uri, inp.options)

def _write_output(df: pd.DataFrame, out) -> None:
    conn = CONNECTORS[out.connector]
    emit("WRITE", {"dataset": out.uri, "connector": out.connector})
    return conn.write(df, out.uri, out.options)

def _run_validations(df: pd.DataFrame, validations):
    for v in validations:
        fn = VALIDATIONS.get(v.type)
        if fn is None:
            raise ValueError(f"Validación no soportada: {v.type}")
        fn(df, v.args if isinstance(v.args, dict) else v.args)

# ---------------------------
# Compliance Hook (PCI-DSS)
# ---------------------------

def _apply_compliance(df: pd.DataFrame, governance: Optional[Dict[str, Any]]) -> pd.DataFrame:
    """
    Aplica compliance si governance.compliance está configurado.
    Actualmente soporta 'pci-dss' usando tu clase PciDssCompliance.
    """
    if not governance:
        return df
    standard = governance.get("compliance")
    if not standard:
        return df

    standard = str(standard).lower().strip()
    if standard != "pci-dss":
        # Futuras normas podrían mapearse aquí
        emit("COMPLIANCE_SKIPPED", {"reason": f"standard '{standard}' no soportado aún"})
        return df

    try:
        # Import perezoso para no acoplar si no se usa compliance
        from godml.compliance_service.pci_dss import PciDssCompliance  # <- tu clase
    except Exception as e:
        raise RuntimeError(
            "Compliance 'pci-dss' solicitado, pero no se pudo importar "
            "godml.compliance_service.pci_dss.PciDssCompliance."
        ) from e

    engine = PciDssCompliance()
    emit("COMPLIANCE_APPLY", {"standard": "pci-dss"})
    out = engine.apply(df.copy())
    return out

# ---------------------------
# Preview & Run
# ---------------------------

def preview_recipe(file: str | Path, limit: int = 20, governance: Optional[Dict[str, Any]] = None):
    """
    Vista previa: aplica transforms y, si corresponde, compliance (pci-dss) antes de mostrar.
    """
    recipe = validate_recipe(file)
    df = _read_input(recipe.inputs[0])
    print(df.head(limit))
    for step in recipe.steps:
        op = TRANSFORMS[step.op]
        df = op.apply(df, **(step.params or {}))
        emit("TRANSFORM", {"op": step.op, "params": step.params or {}})
        print(f"== After {step.op} ==")
        print(df.head(limit))

    # Aplicar compliance en preview para ver el efecto de masking/drops
    df = _apply_compliance(df, governance)
    print("== After COMPLIANCE ==")
    print(df.head(limit))
    return df.head(limit)

def run_recipe(file: str | Path, mode: str = "run", env: str = "dev", governance: Optional[Dict[str, Any]] = None):
    """
    Ejecuta la receta completa:
    1) READ
    2) TRANSFORMS
    3) COMPLIANCE (si governance lo indica)
    4) VALIDATIONS
    5) WRITE (si mode == 'run')
    """
    recipe = validate_recipe(file)
    df = _read_input(recipe.inputs[0])

    for step in recipe.steps:
        op = TRANSFORMS.get(step.op)
        if op is None:
            raise ValueError(f"Transform no soportado: {step.op}")
        df = op.apply(df, **(step.params or {}))
        emit("TRANSFORM", {"op": step.op, "params": step.params or {}})

    # 🔒 Compliance: aplica PCI-DSS (u otros futuros) antes de validar/escribir
    df = _apply_compliance(df, governance)

    _run_validations(df, recipe.validations)

    if mode == "run":
        _write_output(df, recipe.outputs[0])
    return df
