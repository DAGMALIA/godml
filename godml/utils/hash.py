import hashlib

def calculate_file_hash(file_path: str) -> str:
    """
    Calcula el hash SHA256 de un archivo para trazabilidad.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()
