FROM python:3.11-slim

WORKDIR /app

# Copiar todo el contenido del proyecto al contenedor
COPY . .

# Instalar el framework GODML desde setup.py o pyproject.toml
RUN pip install --upgrade pip && \
    pip install .

# Exponer el puerto que usará FastAPI
EXPOSE 8000

# Ejecutar el microservicio
CMD ["python", "godml/deploy_service/main.py"]
