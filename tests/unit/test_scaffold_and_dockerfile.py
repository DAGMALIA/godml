# test_scaffold_and_dockerfile.py
"""
Cubre el arreglo del path de deploy: el Dockerfile generado apuntaba a un tag
hardcodeado que dejó de existir, y `godml init` escribía un `COPY deploy_service`
sobre un directorio que solo creaba `godml deploy`.
"""
import pytest

from godml import __version__
from godml.utils.scaffold import DEPLOY_SERVICE_DIRNAME, scaffold_deploy_service
from godml.utils.yaml_utils import generate_dockerfile_txt


def directivas(dockerfile: str) -> str:
    """
    Devuelve solo las instrucciones, sin comentarios.

    La plantilla documenta en comentarios por qué dejó de heredar de
    dagmalia/godml y menciona el tag 0.4.10 como ejemplo del problema. Esas
    menciones son contexto útil, no configuración: las aserciones tienen que
    mirar lo que Docker ejecuta.
    """
    return "\n".join(
        linea for linea in dockerfile.splitlines() if not linea.lstrip().startswith("#")
    )


class TestScaffoldDeployService:

    def test_crea_el_servicio_desde_la_plantilla(self, tmp_path):
        destino = scaffold_deploy_service(tmp_path)
        assert destino == tmp_path / DEPLOY_SERVICE_DIRNAME
        assert (destino / "server.py").is_file()
        assert (destino / "__init__.py").is_file()

    def test_no_copia_artefactos_de_compilacion(self, tmp_path):
        """__pycache__ de la plantilla no debe viajar al proyecto ni a la imagen."""
        destino = scaffold_deploy_service(tmp_path)
        assert not list(destino.rglob("__pycache__"))
        assert not list(destino.rglob("*.pyc"))

    def test_es_idempotente_y_respeta_customizaciones(self, tmp_path):
        destino = scaffold_deploy_service(tmp_path)
        (destino / "server.py").write_text("# customizado por el usuario", encoding="utf-8")

        scaffold_deploy_service(tmp_path)

        # La copia existe para que el usuario la edite: una segunda llamada no
        # puede pisarla.
        assert (destino / "server.py").read_text(encoding="utf-8") == "# customizado por el usuario"


class TestGenerateDockerfile:

    def test_inyecta_la_version_instalada(self):
        dockerfile = generate_dockerfile_txt()
        assert f'godml[api,observability]=={__version__}' in dockerfile

    def test_no_quedan_placeholders_sin_resolver(self):
        assert "__GODML_VERSION__" not in generate_dockerfile_txt()

    def test_acepta_una_version_explicita(self):
        assert "godml[api,observability]==9.9.9" in generate_dockerfile_txt("9.9.9")

    def test_no_depende_de_la_imagen_preconstruida(self):
        """
        El orden de publicación es librería → PyPI → imagen. Heredar de
        dagmalia/godml obliga a que el último paso ya haya pasado, y si no pasó
        el build falla con "not found". Instalar desde PyPI corta esa dependencia.
        """
        instrucciones = directivas(generate_dockerfile_txt())
        assert "dagmalia/godml" not in instrucciones
        assert instrucciones.count("FROM ") == 1
        assert "FROM python:" in instrucciones

    def test_ejecuta_el_servicio_del_proyecto_no_el_del_paquete(self):
        """
        El CMD debe correr la copia customizable. Si apunta al módulo del
        paquete, el COPY de deploy_service es decorativo y las ediciones del
        usuario nunca se ejecutan.
        """
        dockerfile = generate_dockerfile_txt()
        assert "deploy_service.server:app" in dockerfile
        assert "godml.deploy_service.server:app" not in dockerfile

    def test_copia_lo_necesario_para_servir(self):
        dockerfile = generate_dockerfile_txt()
        for esperado in ("COPY models", "COPY godml.yml", "COPY deploy_service"):
            assert esperado in dockerfile

    def test_los_extras_que_pide_existen_en_el_paquete(self):
        """
        pip no falla ante un extra inexistente: solo emite
        "does not provide the extra 'X'" y sigue. El contenedor se construiría
        sin esa dependencia y la degradación pasaría inadvertida —por ejemplo
        sin prometheus-client, dejando /metrics en no-op—. Este test convierte
        ese warning silencioso en un fallo de CI.
        """
        import re
        import tomllib
        from pathlib import Path

        pedidos = set(
            re.search(r'godml\[([^\]]+)\]', directivas(generate_dockerfile_txt()))
            .group(1)
            .split(",")
        )

        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        disponibles = set(
            tomllib.load(pyproject.open("rb"))["project"]["optional-dependencies"]
        )

        assert pedidos <= disponibles, (
            f"La plantilla pide extras que pyproject.toml no define: {pedidos - disponibles}"
        )


class TestInitGeneraProyectoBuildeable:

    def test_init_crea_el_deploy_service_que_el_dockerfile_copia(self, tmp_path, monkeypatch):
        from godml.cli.commands.init import init_command

        monkeypatch.chdir(tmp_path)
        init_command("proyecto")

        proyecto = tmp_path / "proyecto"
        dockerfile = (proyecto / "Dockerfile").read_text(encoding="utf-8")

        # El COPY y el directorio tienen que ser consistentes: ese desajuste era
        # el que rompía `docker build` apenas se inicializaba un proyecto.
        assert "COPY deploy_service" in dockerfile
        assert (proyecto / DEPLOY_SERVICE_DIRNAME / "server.py").is_file()

    def test_el_dockerfile_generado_no_apunta_a_un_tag_fantasma(self, tmp_path, monkeypatch):
        from godml.cli.commands.init import init_command

        monkeypatch.chdir(tmp_path)
        init_command("proyecto")

        instrucciones = directivas((tmp_path / "proyecto" / "Dockerfile").read_text(encoding="utf-8"))
        assert "0.4.10" not in instrucciones
        assert __version__ in instrucciones
