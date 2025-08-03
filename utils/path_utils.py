import os
from pathlib import Path

import os
import platform
from pathlib import Path


def normalize_path(path: str) -> str:
    """
    Normaliza rutas automáticamente según el sistema operativo.
    """
    # Detectar si estamos en WSL
    is_wsl = "microsoft" in platform.uname().release.lower()
    
    # Si estamos en WSL y la ruta es de Windows, convertir
    if is_wsl and ":" in path and "\\" in path:
        drive, subpath = path.split(":", 1)
        subpath_clean = subpath.replace("\\", "/")
        return os.path.abspath(f"/mnt/{drive.lower()}{subpath_clean}")
    
    # Para todos los demás casos (Windows nativo, Linux, macOS)
    return str(Path(path).expanduser().resolve())