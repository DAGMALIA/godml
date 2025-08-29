import pandas as pd
import os

from godml.dataprep_service.connectors.csv import CSVConnector
from godml.dataprep_service.connectors.parquet import ParquetConnector
from godml.dataprep_service.connectors.s3 import S3Connector

# Dataset de prueba
df = pd.DataFrame({
    "id": [1, 2, 3],
    "producto": ["A", "B", "C"],
    "precio": [10.5, 20.0, 7.25]
})

os.makedirs("tests/bucket", exist_ok=True)

# 1) CSV local
csv_path = "tests/local.csv"
CSVConnector().write(df, csv_path)
print("CSV local leído:\n", CSVConnector().read(csv_path), "\n")

# 2) Parquet local
parquet_path = "tests/local.parquet"
ParquetConnector().write(df, parquet_path)
print("Parquet local leído:\n", ParquetConnector().read(parquet_path), "\n")

# 3) S3-like (con MVP actual que delega a local)
s3_uri = "s3://tests/bucket/ventas.csv"
S3Connector().write(df, s3_uri)
print("S3-like CSV leído:\n", S3Connector().read(s3_uri), "\n")

# 4) (Opcional) S3 real con pandas + s3fs
# df.to_csv("s3://mi-bucket/pruebas/ventas.csv", index=False)
# df2 = pd.read_csv("s3://mi-bucket/pruebas/ventas.csv")
