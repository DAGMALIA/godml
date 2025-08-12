import uuid
from datetime import datetime

def emit(event_type: str, payload: dict):
    # MVP: imprime; en P1, enviar a backend OpenLineage (Marquez).
    print(f"[OPENLINEAGE] {datetime.utcnow().isoformat()} {event_type} id={uuid.uuid4()} payload={payload}")
