# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

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
    """Error de seguridad - path traversal, inyección de código, etc."""
    pass

class ModelLoadError(GodMLError):
    """Error cargando modelo"""
    pass

class ConfigurationError(GodMLError):
    """Error en configuración"""
    pass

class PipelineError(GodMLError):
    """Error en pipeline"""
    pass

class PredictionError(GodMLError):
    """Error en predicción"""
    pass


# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================
def setup_clean_logging():
    """Configurar logging limpio sin warnings molestos"""
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("sagemaker").setLevel(logging.ERROR)
    logging.getLogger("mlflow").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.ERROR)


# ============================================================================
# FORMATO CON COLOR ANSI Y PANEL VISUAL
# ============================================================================
class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    GRAY = "\033[90m"

def colorize(level, msg):
    if not sys.stdout.isatty():
        return msg  # Sin color si no hay terminal interactiva
    if level == "INFO":
        return f"{Ansi.CYAN}{msg}{Ansi.RESET}"
    elif level == "WARNING":
        return f"{Ansi.YELLOW}{msg}{Ansi.RESET}"
    elif level == "ERROR":
        return f"{Ansi.RED}{msg}{Ansi.RESET}"
    elif level == "DEBUG":
        return f"{Ansi.GRAY}{msg}{Ansi.RESET}"
    else:
        return msg

class ColorFormatter(logging.Formatter):
    def format(self, record):
        base = (
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"[{record.levelname}] 🕒 {self.formatTime(record, '%H:%M:%S')} | {record.name}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{record.getMessage()}\n"
            "───────────────────────────────────────────────────────────────────────"
        )
        return colorize(record.levelname, base)


# ============================================================================
# LOGGER PRINCIPAL
# ============================================================================
def get_logger(name: str = "GODML", log_to_file: bool = True) -> logging.Logger:
    """Obtiene el logger formateado y con colores"""
    setup_clean_logging()

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # evitar duplicados

    logger.setLevel(logging.INFO)

    # Handler para consola (con color)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColorFormatter())
    logger.addHandler(console_handler)

    # Handler opcional para archivo rotativo
    if log_to_file:
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "godml.log")
        file_handler = RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        # Formato sin colores para archivo
        file_formatter = logging.Formatter(
            "[%(levelname)s] %(asctime)s | %(name)s\n%(message)s\n" + "-" * 70,
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


# ============================================================================
# LOGGER GLOBAL
# ============================================================================
godml_logger = get_logger()
