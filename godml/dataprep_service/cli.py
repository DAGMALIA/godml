# godml/dataprep_service/cli.py

import typer
from pathlib import Path
from yaml import safe_load
from typing import Optional
from godml.config_service.schema import Governance
from .recipe_executor import validate_recipe, preview_recipe, run_recipe

app = typer.Typer(help="🧩 GODML DataPrep CLI — ejecución y cumplimiento de recetas de datos")

# ---------------------------
# Helper interno
# ---------------------------

def _load_governance_from_yaml(path: Path) -> Optional[dict]:
    """
    Carga y valida el bloque `governance` desde un YAML GODML.
    Devuelve un dict limpio o None si no existe.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            yaml_data = safe_load(f) or {}
        governance_data = yaml_data.get("governance")
        if not governance_data:
            return None

        # Validar y normalizar con el modelo oficial
        gov_model = Governance(**governance_data)
        return gov_model.model_dump()
    except FileNotFoundError:
        raise typer.BadParameter(f"Archivo no encontrado: {path}")
    except Exception as e:
        typer.echo(f"⚠️ Error cargando governance: {e}")
        return None


# ---------------------------
# Comandos principales
# ---------------------------

@app.command()
def validate(file: str):
    """Valida la estructura del recipe YAML sin ejecutarlo."""
    validate_recipe(Path(file))
    typer.echo("✅ Recipe válido.")


@app.command()
def preview(file: str, limit: int = 20):
    """Muestra una vista previa de las transformaciones y el cumplimiento aplicado."""
    path = Path(file)
    governance = _load_governance_from_yaml(path)
    preview_recipe(path, limit, governance=governance)


@app.command()
def dry_run(file: str):
    """Ejecuta la receta sin escribir salida (solo transforma + valida)."""
    path = Path(file)
    governance = _load_governance_from_yaml(path)
    run_recipe(path, mode="dry", governance=governance)
    typer.echo("✅ Dry-run exitoso.")


@app.command()
def run(file: str, env: str = "dev"):
    """Ejecuta la receta completa con cumplimiento (si se define en YAML)."""
    path = Path(file)
    governance = _load_governance_from_yaml(path)
    run_recipe(path, mode="run", env=env, governance=governance)
    typer.echo("✅ Ejecución completada.")


# ---------------------------
# Punto de entrada
# ---------------------------
if __name__ == "__main__":
    app()
