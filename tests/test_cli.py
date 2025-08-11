import shutil
from pathlib import Path
from typer.testing import CliRunner
from godml.godml_cli import app  # O el archivo donde está `app`

runner = CliRunner()

def test_init_crea_estructura_basica(tmp_path):
    project_name = "mi_proyecto_test"
    result = runner.invoke(app, ["init", project_name])
    assert result.exit_code == 0
    assert (tmp_path / project_name / "data").exists()
    assert (tmp_path / project_name / "outputs").exists()
    assert (tmp_path / project_name / "models").exists()
    assert (tmp_path / project_name / "godml.yml").exists()
    assert (tmp_path / project_name / "README.md").exists()
    assert (tmp_path / project_name / "Dockerfile").exists()

def test_calc_hash(tmp_path):
    # Crear archivo de prueba
    file_path = tmp_path / "archivo.csv"
    file_path.write_text("columna\n1\n2\n3\n")
    result = runner.invoke(app, ["calc-hash", str(file_path)])
    assert result.exit_code == 0
    assert "Hash SHA-256" in result.output

def test_run_yaml_sin_dataset(tmp_path):
    yaml_path = tmp_path / "godml.yml"
    yaml_path.write_text("dataset:\n  uri: archivo.csv\n  hash: auto\n")
    archivo = tmp_path / "archivo.csv"
    archivo.write_text("columna\n1\n2\n3\n")
    result = runner.invoke(app, ["run", "-f", str(yaml_path)])
    # Este test puede fallar si `load_pipeline` no está mockeado
    assert result.exit_code != 1  # o lo que corresponda
