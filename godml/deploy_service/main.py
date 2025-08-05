# godml/deploy_service/main.py
import os
import uvicorn
from godml.deploy_service.app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🌐 Iniciando servicio en http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

