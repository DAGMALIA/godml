from __future__ import annotations

import json

import pandas as pd

from godml.advisor_service.advisor_orchestrator import AdvisorOrchestrator
from godml.advisor_service.doc_rag_advisor import DocRAGAdvisor
from godml.advisor_service.metric_judge import MetricJudge
from godml.advisor_service.llm_advisor import LLMAdvisor  # noqa: F401 — re-exported


def advisor(df: pd.DataFrame, target: str | None = None):
    orchestrator = AdvisorOrchestrator(use_rag=False)
    return orchestrator.analyze(df, target)


def advisor_rag(df: pd.DataFrame, target: str | None = None, derive_target: bool = False):
    orchestrator = AdvisorOrchestrator(use_rag=True)
    return orchestrator.analyze(df, target, derive_target)


def doc_advisor(question: str):
    bot = DocRAGAdvisor()
    return bot.ask(question)


def metric_judge(X, y, task_type: str = "classification"):
    judge = MetricJudge()
    df = X.copy()
    target_col = getattr(y, "name", None) or "target"
    df[target_col] = y
    return judge.analyze(df, target_col)


def advisor_full_report(df: pd.DataFrame, target: str | None = None, derive_target: bool = False):
    orch = AdvisorOrchestrator()
    report = orch.analyze(df, target=target, derive_target=derive_target)

    print("\n======================")
    print("GODML FULL REPORT")
    print("======================")

    metrics = report.get("metrics", {})
    print("\n=== Metricas ===")
    print(f"Tipo de tarea: {metrics.get('task_type', 'N/A')}")
    if "metrics" in metrics:
        print("Metricas recomendadas:", ", ".join(metrics["metrics"]))
    if "recipe" in metrics:
        print("Receta minima de DataPrep:")
        print(json.dumps(metrics["recipe"], indent=2, ensure_ascii=False))

    print("\n=== Modelos sugeridos ===")
    for i, model in enumerate(report.get("models", []), 1):
        print(f"{i}. {model}")

    print("\n=== Espacio de hiperparametros ===")
    hyperparams = report.get("hyperparams", {})
    if hyperparams:
        for k, v in hyperparams.items():
            print(f"  - {k}: {v}")
    else:
        print("  (ninguno sugerido)")

    print("\n=== Calidad de datos ===")
    for k, v in report.get("quality", {}).items():
        print(f"  - {k}: {v}")

    print("\n=== Receta LLM (JSON para notebook) ===")
    recipe_llm = report.get("recipe_llm")
    if recipe_llm:
        print(json.dumps(recipe_llm, indent=2, ensure_ascii=False))
    else:
        print("  (no generada)")

    print("\nReporte completo generado.\n")
