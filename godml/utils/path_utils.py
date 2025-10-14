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
    # Validar entrada básica
    if not path or not isinstance(path, str):
        raise SecurityError("Ruta inválida o vacía")
    
    # Detectar patrones peligrosos antes de procesar
    if ".." in path or path.startswith("~"):
        raise SecurityError("Patrón peligroso detectado en ruta")
    
    # Detectar si estamos en WSL
    is_wsl = "microsoft" in platform.uname().release.lower()
    
    try:
        # Si estamos en WSL y la ruta es de Windows, convertir
        if is_wsl and ":" in path and "\\" in path:
            drive, subpath = path.split(":", 1)
            subpath_clean = subpath.replace("\\", "/")
            normalized = os.path.abspath(f"/mnt/{drive.lower()}{subpath_clean}")
        else:
            # Para todos los demás casos (Windows nativo, Linux, macOS)
            normalized = str(Path(path).expanduser().resolve())
        
        return normalized
    except Exception as e:
        raise SecurityError(f"Error normalizando ruta: {str(e)}")


def sanitize_for_log(text: str) -> str:
    """Sanitiza texto para logging seguro removiendo caracteres peligrosos"""
    if not isinstance(text, str):
        text = str(text)
    # Remover caracteres de control y newlines
    sanitized = re.sub(r'[\r\n\t\x00-\x1f\x7f-\x9f]', '', text)
    # Limitar longitud para evitar log flooding
    return sanitized[:500] + "..." if len(sanitized) > 500 else sanitized


def validate_safe_path(path: str, base_dir: Optional[str | Path] = None) -> Path:
    """
    Valida que la ruta sea segura y (si base_dir se provee) que esté contenida dentro de base_dir.
    Retorna un pathlib.Path absoluto.
    """
    if not isinstance(path, str) or not path.strip():
        raise SecurityError("Ruta inválida o vacía")

    # Normaliza a Path absoluto (sin resolver errores si no existe el archivo)
    try:
        p = Path(path).expanduser().resolve(strict=False)  # no falla si no existe
    except Exception as e:
        raise SecurityError(f"No se pudo normalizar la ruta: {e}")

    # Políticas de entrada (opcional endurecimiento)
    # Evita caracteres de control y null bytes
    if any(ord(c) < 32 for c in path) or "\x00" in path:
        raise SecurityError("Caracteres de control o null byte detectados")

    # Si se define base_dir, exige contención
    if base_dir:
        base = Path(base_dir).expanduser().resolve(strict=True)
        try:
            p.relative_to(base)
        except ValueError:
            raise SecurityError("Ruta fuera del directorio permitido")

    # Evita traversal basado en la entrada original (defensa en profundidad)
    # Nota: resolve() ya neutraliza .. y ~, esto es extra-cautela
    dangerous_tokens = [".."]
    if any(tok in Path(path).parts for tok in dangerous_tokens):
        # Usar parts evita falsos positivos en nombres tipo "data..csv"
        raise SecurityError("Path traversal detectado en la ruta de entrada")

    return p


def safe_join(*paths) -> str:
    """Une rutas de forma segura evitando path traversal"""
    if not paths:
        raise SecurityError("No se proporcionaron rutas")
    
    # Validar cada componente
    for path_part in paths:
        if not isinstance(path_part, str) or not path_part:
            raise SecurityError("Componente de ruta inválido")
        if ".." in path_part or path_part.startswith("/"):
            raise SecurityError("Componente de ruta peligroso")
    
    try:
        result = Path(*paths).resolve()
        return str(result)
    except Exception as e:
        raise SecurityError(f"Error uniendo rutas: {str(e)}")
