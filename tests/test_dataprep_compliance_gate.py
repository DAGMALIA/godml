import pandas as pd
from pathlib import Path
from textwrap import dedent

from godml.dataprep_service.recipe_executor import run_recipe

def test_pci_dss_apply_masks_and_drops(tmp_path: Path):
    # Datos con PII típica de PCI
    inp = tmp_path / "input.csv"
    df = pd.DataFrame({
        "id": [1, 2],
        "email": ["user1@example.com", "user2@example.com"],
        "amount": [10.0, 20.0],
        "cvv": ["123", "456"],                  # debe ser DROP
        "expiration_date": ["12/26", "01/27"],  # debe quedar "MM/YY"
    })
    df.to_csv(inp, index=False)

    out_path = tmp_path / "out.csv"
    recipe_path = tmp_path / "recipe.yml"

    recipe_yaml = dedent(f"""
    dataprep:
      inputs:
        - name: raw
          connector: csv
          uri: "{inp.as_posix()}"
      steps:
        - op: safe_cast
          params: {{mapping: {{amount: float}}}}
      validations: []
      outputs:
        - name: clean
          connector: csv
          uri: "{out_path.as_posix()}"
    """).strip()
    recipe_path.write_text(recipe_yaml, encoding="utf-8")

    # Ejecuta con governance -> modo APPLY de PciDssCompliance
    governance = {"compliance": "pci-dss"}
    out_df = run_recipe(recipe_path, mode="run", governance=governance)

    # Se debe haber escrito el archivo
    assert out_path.exists(), "No se generó el archivo de salida"

    # Debe eliminar la columna CVV
    assert "cvv" not in out_df.columns, "La columna 'cvv' debió ser eliminada por PCI-DSS"

    # expiration_date debe estar normalizado como "MM/YY"
    assert out_df["expiration_date"].eq("MM/YY").all(), "expiration_date debió convertirse a 'MM/YY'"

    # email debió ser enmascarado (cambió respecto al original)
    assert not (out_df["email"].astype(str).values == df["email"].astype(str).values).all(), \
        "El email no parece haber sido enmascarado"

def test_transforms_one_hot_drop_duplicates_and_validations(tmp_path: Path):
    inp = tmp_path / "input.csv"
    pd.DataFrame({
        "id": [1, 2, 2, 3],
        "amount": [10, 20, 20, 30],
        "segment": ["F", "M", "M", "F"]
    }).to_csv(inp, index=False)

    out_path = tmp_path / "out.csv"
    recipe_path = tmp_path / "recipe.yml"
    recipe_path.write_text(dedent(f"""
    dataprep:
      inputs:
        - name: raw
          connector: csv
          uri: "{inp.as_posix()}"
      steps:
        - op: drop_duplicates
          params: {{subset: [id], keep: last}}
        - op: one_hot
          params: {{columns: ["segment"], drop_first: false}}
      validations:
        - type: expect_non_null
          args: ["id"]
        - type: expect_unique
          args: ["id"]
        - type: expect_range
          args: {{column: amount, min: 0}}
      outputs:
        - name: clean
          connector: csv
          uri: "{out_path.as_posix()}"
    """).strip(), encoding="utf-8")

    df_out = run_recipe(recipe_path, mode="run")
    assert out_path.exists()
    assert len(df_out) == 3                # drop_duplicates keep=last
    assert "segment_F" in df_out.columns   # one_hot aplicado
    assert "segment_M" in df_out.columns

def test_outlier_flag_regex_replace_minmax_scale(tmp_path: Path):
    inp = tmp_path / "input.csv"
    pd.DataFrame({
        "id": [1, 2, 3, 4],
        "amount": [10.0, 12.0, 11.5, 1000.0],
        "name": [" Alice ", "Bob ", "  Carol", "Da-vid"]
    }).to_csv(inp, index=False)

    out_path = tmp_path / "out.csv"
    recipe_path = tmp_path / "recipe.yml"
    recipe_path.write_text(dedent(f"""
    dataprep:
      inputs:
        - name: raw
          connector: csv
          uri: "{inp.as_posix()}"
      steps:
        - op: regex_replace
          params: {{column: name, pattern: '[\\s-]+', repl: ""}}
        - op: outlier_flag
          params: {{column: amount, method: iqr, threshold: 1.5, new_column: "is_outlier"}}
        - op: minmax_scale
          params: {{columns: ["amount"], feature_range: [0, 1]}}
      validations: []
      outputs:
        - name: clean
          connector: csv
          uri: "{out_path.as_posix()}"
    """).strip(), encoding="utf-8")

    df_out = run_recipe(recipe_path, mode="run")
    assert out_path.exists()
    # Regex limpio
    assert list(df_out["name"]) == ["Alice", "Bob", "Carol", "David"]
    # Outlier marcado
    assert df_out["is_outlier"].dtype == bool
    assert df_out["is_outlier"].sum() == 1
    # MinMax en rango
    assert df_out["amount"].between(0, 1).all()