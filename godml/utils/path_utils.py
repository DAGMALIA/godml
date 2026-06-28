import os
import re
import platform
from pathlib import Path
from typing import Optional


class SecurityError(Exception):
    """Excepción para errores de seguridad"""
    pass


def normalize_path(path: str) -> str:
    """
    Normaliza rutas automáticamente según el sistema operativo de forma segura.
    """
    if not path or not isinstance(path, str):
        raise SecurityError("Ruta inválida o vacía")

    # Null bytes y caracteres de control — detectar ANTES de resolve()
    if "\x00" in path or any(ord(c) < 32 for c in path):
        raise SecurityError("Caracteres de control o null byte detectados")

    # Detectar patrones peligrosos antes de procesar
    if ".." in path or path.startswith("~"):
        raise SecurityError("Patrón peligroso detectado en ruta")

    # Detectar si estamos en WSL
    is_wsl = "microsoft" in platform.uname().release.lower()

    try:
        if is_wsl and ":" in path and "\\" in path:
            drive, subpath = path.split(":", 1)
            subpath_clean = subpath.replace("\\", "/")
            normalized = os.path.abspath(f"/mnt/{drive.lower()}{subpath_clean}")
        else:
            normalized = str(Path(path).expanduser().resolve())

        return normalized
    except Exception as e:
        raise SecurityError(f"Error normalizando ruta: {str(e)}")


def sanitize_for_log(text: str) -> str:
    """Sanitiza texto para logging seguro removiendo caracteres peligrosos"""
    if not isinstance(text, str):
        text = str(text)
    sanitized = re.sub(r'[\r\n\t\x00-\x1f\x7f-\x9f]', '', text)
    return sanitized[:500] + "..." if len(sanitized) > 500 else sanitized


def validate_safe_path(path: str, base_dir: Optional[str | Path] = None) -> Path:
    """
    Valida que la ruta sea segura y (si base_dir se provee) que esté contenida dentro de base_dir.
    Retorna un pathlib.Path absoluto.
    """
    if not isinstance(path, str) or not path.strip():
        raise SecurityError("Ruta inválida o vacía")

    # Null bytes y caracteres de control — detectar ANTES de resolve()
    if "\x00" in path or any(ord(c) < 32 for c in path):
        raise SecurityError("Caracteres de control o null byte detectados")

    # Path traversal — detectar ANTES de resolve() para mensaje claro
    dangerous_tokens = [".."]
    if any(tok in Path(path).parts for tok in dangerous_tokens):
        raise SecurityError("Patrón peligroso detectado en ruta")

    try:
        p = Path(path).expanduser().resolve(strict=False)
    except Exception as e:
        raise SecurityError(f"No se pudo normalizar la ruta: {e}")

    # Si se define base_dir, exige contención
    if base_dir:
        base = Path(base_dir).expanduser().resolve(strict=True)
        try:
            p.relative_to(base)
        except ValueError:
            raise SecurityError("Ruta fuera del directorio permitido")

    return p


def safe_join(*paths) -> str:
    """Une rutas de forma segura evitando path traversal"""
    if not paths:
        raise SecurityError("No se proporcionaron rutas")

    for path_part in paths:
        if not isinstance(path_part, str) or not path_part:
            raise SecurityError("Componente de ruta inválido")
        # Null bytes — detectar ANTES de resolve()
        if "\x00" in path_part or any(ord(c) < 32 for c in path_part):
            raise SecurityError("Caracteres de control o null byte detectados")
        if ".." in path_part or path_part.startswith("/"):
            raise SecurityError("Componente de ruta peligroso")

    try:
        result = Path(*paths).resolve()
        return str(result)
    except Exception as e:
        raise SecurityError(f"Error uniendo rutas: {str(e)}")
