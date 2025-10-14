import typer
from pathlib import Path
from .recipe_executor import validate_recipe, preview_recipe, run_recipe

app = typer.Typer(help="GODML DataPrep CLI (MVP)")

@app.command()
def validate(file: str):
    validate_recipe(Path(file))
    typer.echo("✅ Recipe válido.")

@app.command()
def preview(file: str, limit: int = 20):
    preview_recipe(Path(file), limit)

@app.command()
def dry_run(file: str):
    run_recipe(Path(file), mode="dry")
    typer.echo("✅ Dry-run exitoso.")

@app.command()
def run(file: str, env: str = "dev"):
    run_recipe(Path(file), mode="run", env=env)
    typer.echo("✅ Ejecución completada.")

if __name__ == "__main__":
    app()
