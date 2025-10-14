# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import os
import re
import subprocess
from pathlib import Path
from subprocess import DEVNULL, CalledProcessError
from shutil import which, copytree
from typing import Optional

import typer
import uvicorn
import importlib.resources as pkg_resources
from yaml import safe_load

from godml.deploy_service import server
from godml.utils.hash import calculate_file_hash
from godml.core_service.parser import load_pipeline
from godml.core_service.executors import get_executor
from godml.monitoring_service.logger import get_logger, SecurityError, ConfigurationError
from godml.utils.path_utils import normalize_path, sanitize_for_log, validate_safe_path
from godml.utils.yaml_utils import update_dataset_hash_in_yaml
from godml.utils.yaml_utils import generate_default_yaml, generate_dockerfile_txt, generate_readme_md
from godml.deploy_service.env_config import ENVIRONMENTS
from godml.dataprep_service.cli import app as dataprep_app

logger = get_logger()
app = typer.Typer(help="GODML CLI")

def _validate_docker_available() -> None:
    """Valida que Docker esté disponible y corriendo."""
    docker_path = which("docker")
    if docker_path is None:
        logger.error("❌ Docker no está instalado o no está en PATH.")
        logger.info("💡 Instala Docker desde https://www.docker.com/products/docker-desktop/")
        raise typer.Exit(1)
    
    try:
        if docker_path and ('..' in docker_path or not os.path.isabs(docker_path)):
            raise SecurityError("Ruta Docker no segura")

        if docker_path:
            subprocess.run([docker_path, "info"], stdout=DEVNULL, stderr=DEVNULL, check=True)
    except CalledProcessError:
        logger.error("❌ Docker no está corriendo.")
        logger.info("💡 Abre Docker Desktop y asegúrate de que esté activo.")
        raise typer.Exit(1)

def _load_yaml_config(yaml_path: str) -> dict:
    """Carga y valida configuración YAML."""
    if '..' in yaml_path:
        raise SecurityError("Ruta no permitida")

    if os.path.isabs(yaml_path):
        if not (yaml_path.startswith("/tmp/uploads") or yaml_path.startswith("/data")):
            raise SecurityError(f"Ruta no permitida: {yaml_path}")
    
    safe_yaml_path = validate_safe_path(yaml_path)
    if not safe_yaml_path.exists():
        logger.error(f"❌ No se encontró {sanitize_for_log(yaml_path)} en el directorio actual.")
        raise typer.Exit(1)
    
    try:
        with open(safe_yaml_path, "r", encoding="utf-8") as f:
            return safe_load(f)
    except (IOError, OSError) as e:
        logger.error(f"❌ Error leyendo archivo YAML: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)

def _validate_docker_tag(tag: str) -> str:
    """Valida y sanitiza tag de Docker."""
    safe_tag = re.sub(r'[^a-zA-Z0-9:._-]', '', tag)
    if not re.match(r'^[a-zA-Z0-9:._-]+$', safe_tag):
        raise SecurityError(f"Tag Docker inválido: {sanitize_for_log(safe_tag)}")
    return safe_tag

def _validate_environment_vars(environment: str, host: str, port: str) -> tuple:
    """Valida variables de entorno para Docker."""
    safe_environment = re.sub(r'[^a-zA-Z0-9_-]', '', environment)
    safe_host = re.sub(r'[^a-zA-Z0-9._-]', '', str(host))
    safe_port = re.sub(r'[^0-9]', '', str(port))
    
    if not all([safe_environment, safe_host, safe_port]):
        raise SecurityError("Variables de entorno contienen caracteres inválidos")
    if not re.match(r'^[0-9]+$', safe_port):
        raise SecurityError("Puerto inválido")
    
    return safe_environment, safe_host, safe_port

@app.command()
def run(file: str = typer.Option(..., "--file", "-f", help="Ruta al archivo YAML")):
    """Ejecuta un pipeline GODML desde un archivo YAML."""
    try:
        if '..' in file:
            raise SecurityError("Ruta no permitida")
        
        if os.path.isabs(file):
            if not (file.startswith("/tmp/uploads") or file.startswith("/data")):
                raise SecurityError(f"Ruta no permitida: {file}")

        yaml_path = validate_safe_path(file)
        print(f"📄 Usando archivo YAML: {yaml_path}")

        # Cargar pipeline
        pipeline = load_pipeline(str(yaml_path))
        print(f"📂 Dataset: {pipeline.dataset.uri}")
        print(f"📤 Output: {pipeline.deploy.batch_output}")

        # ✅ Normalización: Si dataset.dataprep está en modo inline, lo convertimos a full
        def normalize_inline_to_full(dataprep: dict, dataset_uri: str) -> dict:
            steps = dataprep.get("steps", []) or []
        
            # Detectar tipo de input
            if dataset_uri.startswith("s3://"):
                connector = "s3"
            elif dataset_uri.endswith(".parquet"):
                connector = "parquet"
            else:
                connector = "csv"
        
            # Detectar entradas/salidas explícitas
            read_step = next((s for s in steps if s.get("op") in ("read_csv", "read_parquet")), None)
            write_step = next((s for s in reversed(steps) if s.get("op") in ("write_csv", "write_parquet")), None)
        
            in_uri = (read_step or {}).get("params", {}).get("path") or dataset_uri
            if write_step and write_step.get("params", {}).get("path"):
                out_uri = write_step["params"]["path"]
            else:
                if connector == "csv":
                    out_uri = dataset_uri[:-4] + "_clean.csv"
                elif connector == "parquet":
                    out_uri = dataset_uri[:-8] + "_clean.parquet"
                else:
                    out_uri = dataset_uri + "_clean"
        
            # Filtramos IO para evitar duplicidad
            core_steps = [s for s in steps if s.get("op") not in ("read_csv", "read_parquet", "write_csv", "write_parquet")]
        
            return {
                "inputs": [{"name": "raw", "connector": connector, "uri": in_uri}],
                "steps": core_steps,
                "outputs": [{"name": "clean", "connector": connector, "uri": out_uri}],
            }


        # Aplicar la conversión si hace falta
        if isinstance(pipeline.dataset.dataprep, dict) and "steps" in pipeline.dataset.dataprep and (
            "inputs" not in pipeline.dataset.dataprep or "outputs" not in pipeline.dataset.dataprep
        ):
            pipeline.dataset.dataprep = normalize_inline_to_full(pipeline.dataset.dataprep, pipeline.dataset.uri)
            print("✅ dataprep inline normalizado a formato completo.")

        # Ejecutar pipeline
        executor = get_executor(pipeline.provider)
        executor.validate(pipeline)
        result = executor.run(pipeline)

        if result is False:
            logger.error("❌ Entrenamiento fallido")
            raise typer.Exit(1)

    except FileNotFoundError as e:
        logger.error(f"❌ Archivo no encontrado: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except ConfigurationError as e:
        logger.error(f"❌ Error de configuración: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)


@app.command("calc-hash")
def calc_hash(
    path: str = typer.Argument(..., help="Ruta al archivo a hashear"),
    update_yaml: Optional[str] = typer.Option(None, "--update-yaml", "-u", help="Ruta a un archivo YAML donde actualizar el hash automáticamente"),
):
    """Calcula el hash SHA-256 de un archivo. Opcionalmente, actualiza un YAML."""
    try:
        if '..' in path or os.path.isabs(path):
            raise SecurityError("Ruta no permitida")
        if update_yaml and ('..' in update_yaml or os.path.isabs(update_yaml)):
            raise SecurityError("Ruta YAML no permitida")
        full_path = validate_safe_path(path)
        hash_value = calculate_file_hash(str(full_path))
        print(f"🔐 Hash SHA-256 para {full_path}:\n{hash_value}")

        if update_yaml:
            yaml_path = validate_safe_path(update_yaml)
            update_dataset_hash_in_yaml(str(yaml_path), hash_value)
            print(f"✅ Hash actualizado en YAML: {yaml_path}")

    except FileNotFoundError as e:
        logger.error(f"❌ Archivo no encontrado: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"❌ Error al calcular hash: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)

@app.command()
def init(project_name: str):
    """Inicializa un nuevo proyecto GODML con soporte de deploy incluido."""
    try:
        if '..' in project_name or os.path.isabs(project_name):
            raise SecurityError("Nombre de proyecto no permitido")
        
        logger.info(f"🚀 Inicializando proyecto GODML: {sanitize_for_log(project_name)}")
        
        safe_project_name = validate_safe_path(project_name, os.getcwd())
        project_path = Path(safe_project_name)
        project_path.mkdir(exist_ok=True)

        # Crear carpetas básicas
        for folder in ["data", "outputs", "models"]:
            folder_path = validate_safe_path(str(project_path / folder))
            Path(folder_path).mkdir(exist_ok=True)

        # Crear YAML con deploy_config incluido automáticamente
        yaml_content = generate_default_yaml(project_name)
        yaml_path = validate_safe_path(str(project_path / "godml.yml"))
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        # Crear README
        readme_content = generate_readme_md(project_name)
        readme_path = validate_safe_path(str(project_path / "README.md"))
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        # Crear Dockerfile por defecto
        dockerfile_path = validate_safe_path(str(project_path / "Dockerfile"))
        if not Path(dockerfile_path).exists():
            dockerfile_content = generate_dockerfile_txt()
            with open(dockerfile_path, "w", encoding="utf-8") as f:
                f.write(dockerfile_content)
        
        logger.info("🐳 Dockerfile generado.")
        logger.info(f"✅ Proyecto '{sanitize_for_log(project_name)}' creado exitosamente.")
        logger.info(f"📁 Ubicación: {sanitize_for_log(str(project_path.absolute()))}")
        logger.info("📋 Próximos pasos:")
        logger.info(f"   cd {sanitize_for_log(project_name)}")
        logger.info("   godml run -f godml.yml")
        logger.info(f"   godml deploy dev {sanitize_for_log(project_name)}")

    except PermissionError as e:
        logger.error(f"❌ Error de permisos: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except OSError as e:
        logger.error(f"❌ Error del sistema: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)

@app.command()
def serve(environment: str = "dev"):
    """Sirve el modelo como microservicio FastAPI leyendo la configuración desde godml.yml"""
    try:
        if '..' in environment or os.path.isabs(environment):
            raise SecurityError("Ambiente no permitido")

        config_yaml = _load_yaml_config("godml.yml")
        deploy_config = config_yaml.get("deploy_config", {})
        
        if environment not in deploy_config:
            logger.error(f"❌ Ambiente '{sanitize_for_log(environment)}' no encontrado en deploy_config.")
            raise typer.Exit(1)

        config = deploy_config[environment]
        
        # Validación explícita y sin fallback
        required_keys = ["host", "port", "docker_tag"]
        missing = [k for k in required_keys if k not in config]
        if missing:
            logger.error(f"❌ Faltan las siguientes claves en 'deploy_config.{sanitize_for_log(environment)}' del godml.yml: {', '.join(missing)}")
            raise typer.Exit(1)
        
        host = config["host"]
        port = config["port"]

        logger.info(f"🚀 Sirviendo modelo en http://{sanitize_for_log(str(host))}:{sanitize_for_log(str(port))}")
        uvicorn.run("godml.deploy_service.server:app", host=host, port=port, reload=True)

    except ConfigurationError as e:
        logger.error(f"❌ Error de configuración: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"❌ Error en serve: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)

def find_model_for_deploy(environment: str) -> Path:
    """Busca el modelo en el directorio del proyecto actual"""
    try:

        if '..' in environment or os.path.isabs(environment):
            raise SecurityError("Ambiente no permitido")
        current_dir = Path.cwd()
        
        # Buscar en diferentes ubicaciones según el ambiente
        search_paths = [
            current_dir / "models" / environment,
            current_dir / "models"
        ]
        
        logger.info(f"🔍 Buscando modelo para ambiente '{sanitize_for_log(environment)}' desde: {sanitize_for_log(str(current_dir))}")
        
        model_patterns = ["*.pkl", "*model*", "*.joblib", "*.pickle"]
        
        for search_path in search_paths:
            if search_path.exists():
                logger.debug(f"📂 Revisando directorio: {sanitize_for_log(str(search_path))}")
                
                for pattern in model_patterns:
                    for model_file in search_path.glob(pattern):
                        if model_file.is_file():
                            logger.info(f"📦 Modelo encontrado: {sanitize_for_log(str(model_file))}")
                            return model_file
        
        # Si no encuentra nada, mostrar información de debug
        logger.error(f"❌ No se encontró modelo para ambiente '{sanitize_for_log(environment)}'")
        logger.error(f"📍 Directorio actual: {sanitize_for_log(str(current_dir))}")
        logger.debug("📂 Directorios buscados:")
        for path in search_paths:
            exists = "✅" if path.exists() else "❌"
            logger.debug(f"   {exists} {sanitize_for_log(str(path))}")
            
        raise FileNotFoundError(f"No se encontró modelo para ambiente '{sanitize_for_log(environment)}'")
        
    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"❌ Error buscando modelo: {sanitize_for_log(str(e))}")
        raise

@app.command()
def deploy(project_name: str, environment: str = typer.Argument(..., help="Ambiente: development, staging o production")):
    """Despliega el modelo como microservicio para un ambiente específico."""
    try:
    
        if '..' in project_name or os.path.isabs(project_name):
            raise SecurityError("Nombre de proyecto no permitido")
        if '..' in environment or os.path.isabs(environment):
            raise SecurityError("Ambiente no permitido")
        
        # Validar Docker
        _validate_docker_available()

        # Cargar configuración YAML
        config_yaml = _load_yaml_config("godml.yml")
        envs = config_yaml.get("deploy_config", {})
        
        if environment not in envs:
            available = ", ".join(envs.keys())
            logger.error(f"❌ Ambiente no encontrado: '{sanitize_for_log(environment)}'. Disponibles: {available}")
            raise typer.Exit(1)

        config = envs[environment]
        tag = config.get("docker_tag", f"godml:{environment}")
        port = config.get("port", 8000)
        host = config.get("host", "0.0.0.0")

        # Validar y sanitizar inputs
        safe_tag = _validate_docker_tag(tag)
        safe_environment, safe_host, safe_port = _validate_environment_vars(environment, host, port)

        # Verificar deploy_service existe
        deploy_path = validate_safe_path("deploy_service")
        if not Path(deploy_path).exists():
            logger.info("📦 Generando deploy_service desde plantilla...")
            with pkg_resources.path("godml.templates.deploy_template", "") as template_path:
                safe_template_path = validate_safe_path(str(template_path))
                copytree(str(safe_template_path), str(deploy_path))

        # Verificar o generar Dockerfile
        dockerfile_path = validate_safe_path("Dockerfile")
        if not Path(dockerfile_path).exists():
            dockerfile_content = generate_dockerfile_txt()
            with open(dockerfile_path, "w", encoding="utf-8") as f:
                f.write(dockerfile_content)

        # Construir imagen Docker
        logger.info(f"📦 Construyendo imagen Docker para {sanitize_for_log(environment)}...")
        docker_path = which("docker")
        if docker_path:
            subprocess.run([docker_path, "build", "-t", safe_tag, "."], check=True)

        # Ejecutar contenedor
        logger.info(f"🚀 Ejecutando contenedor {sanitize_for_log(safe_tag)} en http://{sanitize_for_log(safe_host)}:{sanitize_for_log(safe_port)} ...")
        
        if docker_path:
            subprocess.run([
                docker_path, "run", "--rm",
                "-e", f"GODML_ENV={safe_environment}",
                "-e", f"HOST={safe_host}",
                "-e", f"PORT={safe_port}",
                "-p", f"{safe_port}:{safe_port}",
                safe_tag
            ], check=True)

    except CalledProcessError as e:
        logger.error(f"❌ Error ejecutando Docker: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except SecurityError as e:
        logger.error(f"❌ Error de seguridad: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"❌ Error general: {sanitize_for_log(str(e))}")
        raise typer.Exit(1)

app.add_typer(dataprep_app, name="dataprep")

def main():
    """Función principal para el CLI"""
    app()

if __name__ == "__main__":
    main()
