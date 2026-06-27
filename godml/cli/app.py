from __future__ import annotations

from typing import Optional

import typer

from .commands.run import run_command
from .commands.calc_hash import calc_hash_command
from .commands.init import init_command
from .commands.serve import serve_command
from .commands.deploy import deploy_command
from godml.dataprep_service.cli import app as dataprep_app

app = typer.Typer(help="GODML CLI")


@app.command()
def run(file: str = typer.Option(..., "--file", "-f", help="Ruta al archivo YAML")):
    """Ejecuta un pipeline GODML desde un archivo YAML."""
    run_command(file)


@app.command("calc-hash")
def calc_hash(
    path: str = typer.Argument(..., help="Ruta al archivo a hashear"),
    update_yaml: Optional[str] = typer.Option(None, "--update-yaml", "-u", help="Ruta YAML donde actualizar el hash"),
):
    """Calcula el hash SHA-256 de un archivo."""
    calc_hash_command(path, update_yaml)


@app.command()
def init(project_name: str):
    """Inicializa un nuevo proyecto GODML."""
    init_command(project_name)


@app.command()
def serve(environment: str = "dev"):
    """Sirve el modelo como microservicio FastAPI."""
    serve_command(environment)


@app.command()
def deploy(
    project_name: str,
    environment: str = typer.Argument(..., help="Ambiente: development, staging o production"),
):
    """Despliega el modelo como microservicio para un ambiente específico."""
    deploy_command(project_name, environment)


app.add_typer(dataprep_app, name="dataprep")
