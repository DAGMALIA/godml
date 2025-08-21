# Imagen oficial GODML (solo CLI)
FROM python:3.11-slim

LABEL maintainer="Arturo Gutierrez R. <agtzrubio@dagmalia.com>"
LABEL version="0.4.5"
LABEL description="Imagen oficial del framework GODML para MLOps gobernable"

# Evitar archivos pyc y logs con buffers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y libgomp1 && apt-get clean

# Instalar GODML como root
RUN pip install --upgrade pip && pip install godml

# Crear usuario no-root y carpeta de trabajo
RUN useradd -m godmluser
USER godmluser
WORKDIR /app

# Comando por defecto
ENTRYPOINT ["godml"]
CMD ["--help"]
