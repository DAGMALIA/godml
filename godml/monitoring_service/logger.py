# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT

import logging
import sys
import os
import warnings
from logging.handlers import RotatingFileHandler


# ============================================================================
# EXCEPCIONES PERSONALIZADAS GODML
# ============================================================================
class GodMLError(Exception):
    """Base exception para GodML"""

    pass


class SecurityError(GodMLError):
    pass


class ModelLoadError(GodMLError):
    pass


class ConfigurationError(GodMLError):
    pass


class PipelineError(GodMLError):
    pass


class PredictionError(GodMLError):
    pass


# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================
def setup_clean_logging():
    """Quiet third-party output. Process-wide: call only from the CLI."""
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("sagemaker").setLevel(logging.ERROR)
    logging.getLogger("mlflow").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("godml.model_service").setLevel(logging.WARNING)
    logging.getLogger("godml.core_service").setLevel(logging.WARNING)


# ============================================================================
# FORMATTER LIMPIO
# ============================================================================
_USE_COLOR = sys.stdout.isatty()

_LEVEL_PREFIX = {
    "INFO": ("\033[38;5;99m", "·"),  # indigo ·
    "WARNING": ("\033[93m", "⚠"),  # yellow ⚠
    "ERROR": ("\033[91m", "✗"),  # red ✗
    "DEBUG": ("\033[90m", "›"),  # gray ›
}
_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"


class CleanFormatter(logging.Formatter):
    def format(self, record):
        msg = record.getMessage()
        levelname = record.levelname

        if not _USE_COLOR:
            time = self.formatTime(record, "%H:%M:%S")
            return f"[{time}] {levelname[:1]} {msg}"

        color, symbol = _LEVEL_PREFIX.get(levelname, ("", "·"))
        time = f"{_DIM}{self.formatTime(record, '%H:%M:%S')}{_RESET}"

        # Multi-line messages: indent continuation lines
        lines = msg.splitlines()
        if len(lines) == 1:
            return f"\n  {color}{symbol}{_RESET} {time}  {msg}"

        first = lines[0]
        rest = "\n".join(f"    {_DIM}{ln}{_RESET}" for ln in lines[1:])
        return f"\n  {color}{symbol}{_RESET} {time}  {first}\n{rest}"


# ============================================================================
# LOGGER PRINCIPAL
# ============================================================================
def get_logger(name: str = "GODML", log_to_file: bool = False) -> logging.Logger:
    """Library logger: only a NullHandler, no output config (F1-12).

    Applications decide where logs go (`logging.basicConfig(...)`); the godml
    CLI does it with `configure_cli_logging()`. `log_to_file` is kept for
    backwards compatibility and ignored.
    """
    logger = logging.getLogger(name)
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    return logger


def configure_cli_logging(
    log_dir: str | os.PathLike | None = None, log_to_file: bool = True
) -> logging.Logger:
    """Console (and file) output for the godml CLI. Idempotent.

    Writes to `<log_dir>/godml.log`, `./logs/godml.log` by default.
    """
    setup_clean_logging()
    logger = get_logger()
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in [h for h in logger.handlers if getattr(h, "_godml_cli", False)]:
        logger.removeHandler(handler)
        handler.close()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CleanFormatter())
    handlers: list[logging.Handler] = [console_handler]

    if log_to_file:
        target_dir = (
            os.fspath(log_dir) if log_dir else os.path.join(os.getcwd(), "logs")
        )
        os.makedirs(target_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(target_dir, "godml.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter(
                "[%(levelname)s] %(asctime)s  %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handlers.append(file_handler)

    for handler in handlers:
        handler._godml_cli = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return logger


# ============================================================================
# RICH HELPERS  (llamados explícitamente desde mlflow.py para paneles clave)
# ============================================================================
def print_pipeline_start(name: str, dataset: str, output: str) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        c = Console()
        body = Text()
        body.append("  pipeline  ", style="bold white on #4f46e5")
        body.append(f"  {name}\n", style="bold")
        body.append(f"  dataset   {dataset}\n", style="dim")
        body.append(f"  output    {output}", style="dim")
        c.print(Panel(body, border_style="#4f46e5", padding=(0, 1)))
    except Exception:  # noqa: BLE001
        print(f"\n  ▶ {name}  |  {dataset}\n")


def print_metrics_table(metrics: dict, thresholds: dict | None = None) -> None:
    try:
        from rich.console import Console
        from rich.table import Table

        c = Console()
        t = Table(
            show_header=True, header_style="bold #4f46e5", box=None, padding=(0, 2)
        )
        t.add_column("metric", style="dim")
        t.add_column("value", justify="right")
        t.add_column("threshold", justify="right", style="dim")
        t.add_column("", justify="center")

        for metric, value in metrics.items():
            threshold = (thresholds or {}).get(metric)
            thr_str = f"{threshold:.2f}" if threshold is not None else "—"
            if threshold is None:
                icon = ""
            elif value >= threshold:
                icon = "[green]✓[/green]"
            else:
                icon = "[red]✗[/red]"
            t.add_row(metric, f"{value:.4f}", thr_str, icon)

        print()
        c.print(t)
        print()
    except Exception:  # noqa: BLE001
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")


def print_pipeline_result(
    success: bool, name: str, metrics: dict, output: str | None
) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        c = Console()
        if success:
            body = Text()
            body.append("  ✓ Pipeline completado\n\n", style="bold green")
            if "auc" in metrics or "accuracy" in metrics:
                body.append(f"  AUC       {metrics.get('auc', 0):.4f}\n", style="bold")
                body.append(
                    f"  Accuracy  {metrics.get('accuracy', 0):.4f}\n", style="bold"
                )
            else:
                # Pipeline de regresión (p.ej. lstm_forecast, linear_regression):
                # no hay auc/accuracy, muestra las métricas que sí se calcularon.
                for key in ("r2", "mse", "mae"):
                    if key in metrics:
                        body.append(
                            f"  {key.upper():<9} {metrics[key]:.4f}\n", style="bold"
                        )
            if output:
                body.append(f"\n  Output → {output}", style="dim")
            c.print(
                Panel(
                    body,
                    border_style="green",
                    title=f"[bold green]{name}[/bold green]",
                    padding=(0, 1),
                )
            )
        else:
            body = Text()
            body.append("  ✗ Métricas insuficientes\n\n", style="bold red")
            body.append("  Ajusta los thresholds en godml.yml\n", style="dim")
            body.append("  o mejora el dataset con dataset.dataprep", style="dim")
            c.print(
                Panel(
                    body,
                    border_style="red",
                    title=f"[bold red]{name}[/bold red]",
                    padding=(0, 1),
                )
            )
    except Exception:  # noqa: BLE001
        status = "✓ OK" if success else "✗ FAILED"
        print(f"\n  {status}  {name}\n")


# ============================================================================
# LOGGER GLOBAL
# ============================================================================
godml_logger = get_logger()
