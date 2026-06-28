"""GODML Notebook API — thin, notebook-friendly facade over all GODML services."""
from .dataprep import dataprep_preview, dataprep_run, dataprep_run_inline
from .training import train_model, predict, evaluate, compare_models
from .compliance import apply_compliance
from .artifacts import save_artifact, load_artifact, emit_lineage, summarize_df, plot_roc_pr_curves
from .tuning import suggest_search_space, tune_model, optimize_threshold
from .pipeline import (
    GodmlNotebook,
    quick_train,
    quick_train_with_metrics,
    train_from_yaml,
    quick_train_yaml,
)
from .advisor import advisor, advisor_rag, doc_advisor, metric_judge, advisor_full_report

__all__ = [
    # dataprep
    "dataprep_preview",
    "dataprep_run",
    "dataprep_run_inline",
    # training
    "train_model",
    "predict",
    "evaluate",
    "compare_models",
    # compliance
    "apply_compliance",
    # artifacts & utils
    "save_artifact",
    "load_artifact",
    "emit_lineage",
    "summarize_df",
    "plot_roc_pr_curves",
    # tuning
    "suggest_search_space",
    "tune_model",
    "optimize_threshold",
    # pipeline
    "GodmlNotebook",
    "quick_train",
    "quick_train_with_metrics",
    "train_from_yaml",
    "quick_train_yaml",
    # advisor
    "advisor",
    "advisor_rag",
    "doc_advisor",
    "metric_judge",
    "advisor_full_report",
]
