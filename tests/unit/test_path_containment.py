# test_path_containment.py
"""
F1-13: path checks compared strings with `startswith`, so a sibling directory
sharing the prefix (`/proj-evil` vs `/proj`) passed as "inside the project".
The CLI also froze its safe base dirs at import time.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from godml.core.logger import SecurityError


@pytest.fixture
def project(tmp_path, monkeypatch):
    """cwd = <tmp>/proj, plus a sibling <tmp>/proj-evil that shares the prefix."""
    proj, evil = tmp_path / "proj", tmp_path / "proj-evil"
    proj.mkdir()
    evil.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    return proj, evil


class TestCliSafeAbsolutePath:
    def test_sibling_with_same_prefix_is_rejected(self, project):
        from godml.cli.validators import _is_safe_absolute_path

        _, evil = project
        assert _is_safe_absolute_path(str(evil / "godml.yml")) is False

    def test_path_inside_cwd_is_accepted(self, project):
        from godml.cli.validators import _is_safe_absolute_path

        proj, _ = project
        assert _is_safe_absolute_path(str(proj / "godml.yml")) is True

    def test_uses_cwd_at_call_time(self, project, tmp_path, monkeypatch):
        """The base dirs were resolved once at import; a later chdir was ignored."""
        from godml.cli.validators import _is_safe_absolute_path

        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.chdir(other)
        assert _is_safe_absolute_path(str(other / "godml.yml")) is True
        assert _is_safe_absolute_path(str(project[0] / "godml.yml")) is False


@pytest.mark.parametrize(
    "module",
    ["godml.serve.deploy.server", "godml.templates.deploy_template.server"],
)
class TestServerValidateModelPath:
    def load(self, module):
        import importlib

        return importlib.import_module(module).validate_model_path

    def test_sibling_with_same_prefix_is_rejected(self, project, module):
        _, evil = project
        model = evil / "model.pkl"
        model.write_bytes(b"not a real pickle")
        with pytest.raises(SecurityError):
            self.load(module)(model)

    def test_model_inside_project_is_accepted(self, project, module):
        proj, _ = project
        model = proj / "model.pkl"
        model.write_bytes(b"x")
        self.load(module)(model)


def link_dir(link, target) -> None:
    """Directory symlink; on Windows without symlink privilege, a junction
    (no admin needed) so the test runs everywhere instead of being skipped."""
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        if sys.platform != "win32":
            raise
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
        )


class TestLocalModelLoader:
    def test_symlinked_models_dir_to_sibling_is_rejected(self, project):
        from godml.serve.model_loader import load_custom_model_class

        proj, evil = project
        (evil / "custom_model.py").write_text("raise SystemExit('executed')\n")
        link_dir(proj / "models", evil)  # models/ -> <tmp>/proj-evil
        with pytest.raises(SecurityError):
            load_custom_model_class(str(proj), "custom_model", "local")
