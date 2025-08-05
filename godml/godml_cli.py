# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import typer
import shutil
import uvicorn
from pathlib import Path
from godml.deploy_service import server
from godml.utils.hash import calculate_file_hash
from godml.core_service.parser import load_pipeline
from godml.core_service.executors import get_executor
from godml.monitoring_service.logger import get_logger
from godml.utils.path_utils import normalize_path
from godml.utils.yaml_utils import update_dataset_hash_in_yaml
from godml.utils.yaml_utils import generate_default_yaml
from godml.utils.yaml_utils import generate_readme_md
import subprocess
from godml.deploy_service.env_config import ENVIRONMENTS

logger = get_logger()

app = typer.Typer()

@app.command()
def run(file: str = typer.Option(..., "--file", "-f", help="Ruta al archivo YAML")):
    """
    Ejecuta un pipeline GODML desde un archivo YAML.
    """
    try:
        yaml_path = normalize_path(file)
        print(f"📄 Usando archivo YAML: {yaml_path}")

        # 1️⃣ Calcular hash si está en modo automático
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_dict = yaml.safe_load(f)
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
    """
    Calcula el hash SHA-256 de un archivo. Opcionalmente, actualiza un YAML.
    """
    try:
        full_path = normalize_path(path)
        from utils.hash import calculate_file_hash
        hash_value = calculate_file_hash(full_path)
        print(f"🔐 Hash SHA-256 para {full_path}:\n{hash_value}")

        if update_yaml:
            from utils.yaml_utils import update_dataset_hash_in_yaml
            yaml_path = normalize_path(update_yaml)
            update_dataset_hash_in_yaml(yaml_path, hash_value)
            print(f"✅ Hash actualizado en YAML: {yaml_path}")

    except Exception as e:
        logger.error(f"❌ Error al calcular hash: {e}")
        raise typer.Exit(1)



@app.command()
def init(project_name: str):
    """
    Inicializa un nuevo proyecto GODML usando definición automática del YAML.
    """
    logger.info(f"🚀 Inicializando proyecto GODML: {project_name}")
    
    # Crear estructura del proyecto
    project_path = Path(project_name)
    project_path.mkdir(exist_ok=True)

    for folder in ["data", "outputs", "models"]:
        (project_path / folder).mkdir(exist_ok=True)

    # Generar YAML con todas las opciones desde schema
    yaml_content = generate_default_yaml(project_name)
    with open(project_path / "godml.yml", "w", encoding="utf-8") as f:
        f.write(yaml_content)
    
    readme_content = generate_readme_md(project_name)
    with open(project_path / "README.md", "w", encoding="utf-8") as f:
      f.write(readme_content)

    logger.info(f"✅ Proyecto {project_name} creado exitosamente!")
    logger.info(f"📁 Ubicación: {project_path.absolute()}")
    logger.info("📋 Próximos pasos:")
    logger.info(f"   cd {project_name}")
    logger.info("   godml run -f godml.yml")

@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 8000
):
    """
    Sirve el modelo como microservicio FastAPI desde models/production/model.pkl
    """

    logger.info(f"🚀 Sirviendo modelo en http://{host}:{port}")
    uvicorn.run("godml.deploy_service.server:app", host=host, port=port, reload=True)

@app.command()
def deploy(environment: str = typer.Argument(..., help="Ambiente: development, staging o production")):
    """
    Despliega el modelo como microservicio para un ambiente específico.
    """
    if environment not in ENVIRONMENTS:
        logger.error(f"❌ Ambiente no reconocido: {environment}")
        raise typer.Exit(1)

    config = ENVIRONMENTS[environment]
    tag = config["docker_tag"]
    port = config["port"]
    host = config.get("host", "0.0.0.0")

    # Ruta raíz del proyecto (donde está el Dockerfile)
    ROOT_DIR = Path(__file__).resolve().parent.parent
    _DOCKERFILE_PATH = ROOT_DIR / "Dockerfile"
    MODEL_PATH = ROOT_DIR / "models" / "production" / "model.pkl"

    # Validación previa del modelo
    if not MODEL_PATH.exists():
        logger.error(f"❌ No se encontró el modelo en {MODEL_PATH.resolve()}")
        raise typer.Exit(1)

    # Construir imagen Docker
    print(f"📦 Construyendo imagen Docker para {environment}...")
    subprocess.run([
        "docker", "build",
        "-t", tag,
        "."
    ], cwd=str(ROOT_DIR), check=True)
    # Ejecutar contenedor
    print(f"🚀 Ejecutando contenedor {tag} en http://{host}:{port}...")
    subprocess.run([
        "docker", "run", "--rm",
        "-e", f"PORT={port}",
        "-e", f"HOST={host}",
        "-p", f"{port}:{port}",
        tag
    ])



def main():
    """Función principal para el CLI"""
    app()

if __name__ == "__main__":
    main()
