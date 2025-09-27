import pandas as pd
import matplotlib.pyplot as plt

def test_plot_benchmarks():
    # 📥 Cargar resultados previos
    df = pd.read_csv("benchmark_scaling.csv")

    # -------------------------------
    # 1) Gráfico normalizado
    # -------------------------------
    df["time_per_1k"] = df["time_sec"] / (df["data_size"] / 1000)

    plt.figure(figsize=(10,6))
    for step in ["CSV write", "CSV read", "Parquet write", "RegexReplace", "expect_regex"]:
        subset = df[df["step"] == step]
        plt.plot(subset["data_size"], subset["time_per_1k"], marker="o", label=step)

    plt.title("Tiempo normalizado (segundos por 1k filas)")
    plt.xlabel("Tamaño de dataset (filas)")
    plt.ylabel("Tiempo / 1k filas (s)")
    plt.legend()
    plt.grid(True)
    plt.savefig("benchmark_normalizado.png")
    print("Gráfico normalizado guardado en benchmark_normalizado.png")

    # -------------------------------
    # 2) Gráfico log-log
    # -------------------------------
    plt.figure(figsize=(10,6))
    for step in ["CSV write", "CSV read", "Parquet write", "RegexReplace", "expect_regex"]:
        subset = df[df["step"] == step]
        plt.loglog(subset["data_size"], subset["time_sec"], marker="o", label=step, base=10)

    plt.title("Escalado log-log de operaciones (dataprep_service)")
    plt.xlabel("Tamaño de dataset (filas) [log]")
    plt.ylabel("Tiempo de ejecución (s) [log]")
    plt.legend()
    plt.grid(True, which="both")
    plt.savefig("benchmark_loglog.png")
    print("✅ Gráfico log-log guardado en benchmark_loglog.png")
