# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import os
import re
import typer
import shutil
import uvicorn
import subprocess
from pathlib import Path
from godml.deploy_service import server
from godml.utils.hash import calculate_file_hash
from godml.core_service.parser import load_pipeline
from godml.core_service.executors import get_executor
from godml.monitoring_service.logger import get_logger, SecurityError, ConfigurationError
from godml.utils.path_utils import normalize_path, sanitize_for_log, validate_safe_path
from godml.utils.yaml_utils import update_dataset_hash_in_yaml
from godml.utils.yaml_utils import generate_default_yaml,generate_dockerfile_txt, generate_readme_md
import importlib.resources as pkg_resources
from godml.deploy_service.env_config import ENVIRONMENTS
from yaml import safe_load

logger = get_logger()

app = typer.Typer()

@app.command()
def run(file: str = typer.Option(..., "--file", "-f", help="Ruta al archivo YAML")):
    """Ejecuta un pipeline GODML desde un archivo YAML."""
    try:
        yaml_path = normalize_path(file)
        print(f"📄 Usando archivo YAML: {yaml_path}")

        # Calcular hash si está en modo automático
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_dict = safe_load(f)
        dataset_path = normalize_path(yaml_dict['dataset']['uri'])
        if yaml_dict['dataset'].get('hash', 'auto') == 'auto':
            new_hash = calculate_file_hash(dataset_path)
            update_dataset_hash_in_yaml(yaml_path, new_hash)
            print(f"🔑 Hash calculado e insertado en YAML: {new_hash}")

        pipeline = load_pipeline(yaml_path)

        print(f"📂 Dataset: {pipeline.dataset.uri}")
        print(f"📤 Output: {pipeline.deploy.batch_output}")

        executor = get_executor(pipeline.provider)
        executor.validate(pipeline)
        result = executor.run(pipeline)

        if result is False:
            logger.error("❌ Entrenamiento fallido")
            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise typer.Exit(1)

@app.command("calc-hash")
def calc_hash(
    path: str = typer.Argument(..., help="Ruta al archivo a hashear"),
    update_yaml: str = typer.Option(None, "--update-yaml", "-u", help="Ruta a un archivo YAML donde actualizar el hash automáticamente"),
):
    """Calcula el hash SHA-256 de un archivo. Opcionalmente, actualiza un YAML."""
    try:
        full_path = normalize_path(path)
        hash_value = calculate_file_hash(full_path)
        print(f"🔐 Hash SHA-256 para {full_path}:\n{hash_value}")

        if update_yaml:
            yaml_path = normalize_path(update_yaml)
            update_dataset_hash_in_yaml(yaml_path, hash_value)
            print(f"✅ Hash actualizado en YAML: {yaml_path}")

    except Exception as e:
        logger.error(f"❌ Error al calcular hash: {e}")
        raise typer.Exit(1)

@app.command()
def init(project_name: str):
    """Inicializa un nuevo proyecto GODML con soporte de deploy incluido."""
    logger.info(f"🚀 Inicializando proyecto GODML: {sanitize_for_log(project_name)}")
    
    safe_project_name = validate_safe_path(project_name, os.getcwd())
    project_path = Path(safe_project_name)
    project_path.mkdir(exist_ok=True)

    # Crear carpetas básicas
    for folder in ["data", "outputs", "models"]:
        (project_path / folder).mkdir(exist_ok=True)

    # Crear YAML con deploy_config incluido automáticamente
    yaml_content = generate_default_yaml(project_name)
    yaml_path = project_path / "godml.yml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    # Crear README
    readme_content = generate_readme_md(project_name)
    with open(project_path / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    # Copiar deploy_service/ desde plantilla
    deploy_path = project_path / "deploy_service"
    if not deploy_path.exists():
        try:
            with pkg_resources.path("godml.templates.deploy_template", "") as template_path:
                shutil.copytree(template_path, deploy_path)
                logger.info("📦 deploy_service/ copiado desde plantilla.")
        except Exception as e:
            logger.error(f"❌ Error copiando deploy_service/: {e}")

    # Crear Dockerfile por defecto
    dockerfile_path = project_path / "Dockerfile"
    if not dockerfile_path.exists():
        dockerfile_content = generate_dockerfile_txt(project_name)
        with open(project_path / "Dockerfile", "w", encoding="utf-8") as f:
            f.write(dockerfile_content)    
    logger.info("🐳 Dockerfile generado.")

    logger.info(f"✅ Proyecto '{project_name}' creado exitosamente.")
    logger.info(f"📁 Ubicación: {project_path.absolute()}")
    logger.info("📋 Próximos pasos:")
    logger.info(f"   cd {project_name}")
    logger.info("   godml run -f godml.yml")
    logger.info("   godml deploy dev")


@app.command()
def serve(environment: str = "dev"):
    """Sirve el modelo como microservicio FastAPI leyendo la configuración desde godml.yml"""
    try:
        yaml_path = Path("godml.yml")
        if not yaml_path.exists():
            logger.error("❌ No se encontró godml.yml en el directorio actual.")
            raise typer.Exit(1)

        with open(yaml_path, "r", encoding="utf-8") as f:
            config_yaml = safe_load(f)

        deploy_config = config_yaml.get("deploy_config", {})
        if environment not in deploy_config:
            logger.error(f"❌ Ambiente '{environment}' no encontrado en deploy_config.")
            raise typer.Exit(1)

        config = deploy_config[environment]
        
        # Validación explícita y sin fallback
        required_keys = ["host", "port", "docker_tag"]
        missing = [k for k in required_keys if k not in config]
        if missing:
            logger.error(f"❌ Faltan las siguientes claves en 'deploy_config.{environment}' del godml.yml: {', '.join(missing)}")
            raise typer.Exit(1)
        
        host = config["host"]
        port = config["port"]

        logger.info(f"🚀 Sirviendo modelo en http://{host}:{port}")
        uvicorn.run("godml.deploy_service.server:app", host=host, port=port, reload=True)

    except Exception as e:
        logger.error(f"❌ Error en serve: {e}")
        raise typer.Exit(1)


def find_model_for_deploy(environment: str) -> Path:
    """Busca el modelo en el directorio del proyecto actual"""
    try:
        # Usar directorio actual del proyecto, no el de instalación
        current_dir = Path.cwd()
        
        # Buscar en diferentes ubicaciones según el ambiente
        search_paths = [
            current_dir / "models" / environment,
            current_dir / "models" / "prod",
            current_dir / "models" / "qa",
            current_dir / "models" / "dev",
            current_dir / "models"
        ]
        
        logger.info(f"🔍 Buscando modelo para ambiente '{environment}' desde: {current_dir}")
        
        for search_path in search_paths:
            if search_path.exists():
                logger.info(f"📂 Revisando directorio: {search_path}")
                
                # Buscar archivos de modelo
                model_patterns = ["*.pkl", "*model*", "*.joblib", "*.pickle"]
                
                for pattern in model_patterns:
                    for model_file in search_path.glob(pattern):
                        if model_file.is_file():
                            logger.info(f"📦 Modelo encontrado: {model_file}")
                            return model_file
        
        # Si no encuentra nada, mostrar información de debug
        logger.error(f"❌ No se encontró modelo para ambiente '{environment}'")
        logger.error(f"📍 Directorio actual: {current_dir}")
        logger.error("📂 Directorios buscados:")
        for path in search_paths:
            exists = "✅" if path.exists() else "❌"
            logger.error(f"   {exists} {path}")
            
        raise FileNotFoundError(f"No se encontró modelo para ambiente '{environment}'")
        
    except Exception as e:
        logger.error(f"❌ Error buscando modelo: {e}")
        raise

@app.command()
def deploy(project_name: str,environment: str = typer.Argument(..., help="Ambiente: development, staging o production")):
    """Despliega el modelo como microservicio para un ambiente específico."""
    try:
        # Cargar config del YAML
        yaml_path = Path("godml.yml")
        if not yaml_path.exists():
            logger.error("❌ No se encontró godml.yml en el directorio actual.")
            raise typer.Exit(1)

        with open(yaml_path, "r", encoding="utf-8") as f:
            config_yaml = safe_load(f)

        envs = config_yaml.get("deploy_config", {})
        if environment not in envs:
            available = ", ".join(envs.keys())
            logger.error(f"❌ Ambiente no encontrado: '{environment}'. Disponibles: {available}")
            raise typer.Exit(1)

        config = envs[environment]
        tag = config.get("docker_tag", f"godml:{environment}")
        port = config.get("port", 8000)
        host = config.get("host", "0.0.0.0")

        # Verifica si deploy_service existe, si no lo genera
        deploy_path = Path("deploy_service")
        if not deploy_path.exists():
            logger.info("📦 Generando deploy_service desde plantilla...")
            with pkg_resources.path("godml.templates.deploy_template", "") as template_path:
                shutil.copytree(template_path, deploy_path)

        # Verificar o generar Dockerfile
        dockerfile_path = Path("Dockerfile")
        if not dockerfile_path.exists():
            dockerfile_content = generate_dockerfile_txt(project_name)
            with open(dockerfile_path / "Dockerfile", "w", encoding="utf-8") as f:
                f.write(dockerfile_content)

        # Build Docker image
        logger.info(f"📦 Construyendo imagen Docker para {environment}...")
        safe_tag = re.sub(r'[^a-zA-Z0-9:._-]', '', tag)  # Solo caracteres seguros
        subprocess.run(["docker", "build", "-t", safe_tag, "."], check=True)

        # Run Docker container
        logger.info(f"🚀 Ejecutando contenedor {tag} en http://{host}:{port} ...")
        subprocess.run([
            "docker", "run", "--rm",
            "-e", f"GODML_ENV={environment}",
            "-e", f"HOST={host}",
            "-e", f"PORT={port}",
            "-p", f"{port}:{port}",
            tag
        ])


    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error ejecutando Docker: {e}")
        raise typer.Exit(1)

    except Exception as e:
        logger.error(f"❌ Error en deploy: {e}")
        raise typer.Exit(1)

def main():
    """Función principal para el CLI"""
    app()

if __name__ == "__main__":
    main()

