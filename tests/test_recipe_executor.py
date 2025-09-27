import time
import pandas as pd
import tempfile, os

from godml.dataprep_service.connectors.csv import CSVConnector
from godml.dataprep_service.connectors.parquet import ParquetConnector
from godml.dataprep_service.transforms import (
    columns, dedup, encode, missing, quality, scale, text, window
)
from godml.dataprep_service.validators import expectations, schema_checks
from godml.dataprep_service.transforms import cast_types


def run_benchmark(data_size: int, results: list):
    df = pd.DataFrame({
        "id": range(data_size),
        "value": range(data_size),
        "category": ["A", "B", "C", "D"] * (data_size // 4),
        "text": ["hola mundo"] * data_size,
    })

    tmpdir = tempfile.mkdtemp()
    csv_path = os.path.join(tmpdir, "sample.csv")
    parquet_path = os.path.join(tmpdir, "sample.parquet")

    csv_conn = CSVConnector()
    parquet_conn = ParquetConnector()

    def record(name, callable_fn, *args, **kwargs):
        start = time.time()
        callable_fn(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[{data_size}] ⏱️ {name}: {elapsed:.4f} s")
        results.append({
            "data_size": data_size,
            "step": name,
            "time_sec": round(elapsed, 4),
        })


    # I/O
    record("CSV write", df.to_csv, csv_path, index=False)
    record("CSV read", csv_conn.read, csv_path)
    record("Parquet write", parquet_conn.write, df, parquet_path)

    # Transforms
    record("DropColumns", columns.DropColumns().apply, df, columns=["id"])
    record("Rename", columns.Rename().apply, df, mapping={"value": "valor"})
    record("SelectColumns", columns.SelectColumns().apply, df, columns=["id", "value"])
    record("DropDuplicates", dedup.DropDuplicates().apply, df, subset=["id"])
    record("LabelEncode", encode.LabelEncode().apply, df, columns=["category"])
    record("OneHot", encode.OneHot().apply, df, columns=["category"], drop_first=True)
    record("DropNA", missing.DropNA().apply, df, columns=["value"])
    record("FillNA value=0", missing.FillNA().apply, df, columns="value", value=0)
    record("FillNA multi", missing.FillNA().apply, df, columns=["value", "category"], value="X")
    record("FillNA global", missing.FillNA().apply, df, value="MISSING")
    record("OutlierFlag", quality.OutlierFlag().apply, df, column="value")
    record("StandardScale", scale.StandardScale().apply, df, columns=["value"])
    record("MinMaxScale", scale.MinMaxScale().apply, df, columns=["value"])
    record("Lower", text.Lower().apply, df, column="text")
    record("Strip", text.Strip().apply, df, column="text")
    record("RegexReplace", text.RegexReplace().apply, df, column="text", pattern="hola", repl="hi")
    record("CastTypes", cast_types.CastTypes().apply, df, columns={"value": "float"})
    record("Lag", window.Lag().apply, df, column="value", window=5, func="mean")

    # Validators
    record("expect_non_null", expectations.expect_non_null, df, "value")
    record("expect_unique", expectations.expect_unique, df, "id")
    record("expect_range", expectations.expect_range, df, "value", 0, 1_000_000)
    record("expect_regex", expectations.expect_regex, df, "category", r"[A-D]")
    record("check_types", schema_checks.check_types, df, {"id": "int64", "value": "int64"})


def test_benchmark_scaling(tmp_path):
    sizes = [10_000, 50_000, 100_000, 200_000]
    results = []

    for size in sizes:
        print(f"\n🚀 Ejecutando benchmark con DATA_SIZE={size}")
        run_benchmark(size, results)

    out_file = tmp_path / "benchmark_scaling.csv"
    pd.DataFrame(results).to_csv(out_file, index=False)
    print(f"\n🎉 Resultados exportados a {out_file}")

