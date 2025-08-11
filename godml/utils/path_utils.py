import os
import re
import platform
from pathlib import Path

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


def validate_safe_path(path: str, base_dir: str = None) -> str:
    """Valida que la ruta sea segura y no contenga path traversal"""
    if not path or not isinstance(path, str):
        raise SecurityError("Ruta inválida o vacía")
    
    try:
        # Verificar patrones peligrosos en la entrada original
        dangerous_patterns = ["..", "~", "$", "|", "&", ";", "`"]
        for pattern in dangerous_patterns:
            if pattern in path:
                raise SecurityError(f"Patrón peligroso detectado: {pattern}")
        
        # Normalizar la ruta de forma segura
        normalized = Path(path).resolve()
        
        # Si se especifica un directorio base, verificar que esté dentro
        if base_dir:
            base_resolved = Path(base_dir).resolve()
            try:
                normalized.relative_to(base_resolved)
            except ValueError:
                raise SecurityError(f"Ruta fuera del directorio permitido")
                
        return str(normalized)
        
    except SecurityError:
        raise  # Re-lanzar errores de seguridad
    except Exception as e:
        raise SecurityError(f"Error validando ruta: {str(e)}")


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
