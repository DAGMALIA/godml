# test_compat_shims.py
"""
F2-01: every GoDML 1.x import path keeps working through a shim that emits
GoDMLDeprecationWarning (attributed to the importing code) and resolves to
the module at its pillar path.
"""

import ast
import importlib
import re
import sys
import warnings
from pathlib import Path

import pytest

from godml.core.deprecation import GoDMLDeprecationWarning

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "godml"
HELPERS = {"alias_module", "reexport_package", "warn_split_package"}


def discover_shims() -> list[tuple[str, str, str | None]]:
    """(helper, old module, new module) for each shim file in the package."""
    shims = []
    for path in sorted(PACKAGE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in HELPERS
            ):
                args = [a.value for a in node.args if isinstance(a, ast.Constant)]
                shims.append(
                    (node.func.id, args[0], args[1] if len(args) > 1 else None)
                )
    return shims


SHIMS = discover_shims()
MODULES = [(old, new) for helper, old, new in SHIMS if helper == "alias_module"]
PACKAGES = [(old, new) for helper, old, new in SHIMS if helper == "reexport_package"]
SPLIT = [old for helper, old, _ in SHIMS if helper == "warn_split_package"]


def fresh_import(name: str):
    """Import `name` again so its shim runs (and warns) once more."""
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def import_or_skip(name: str):
    try:
        return importlib.import_module(name)
    except ImportError as exc:  # optional extra not installed
        pytest.skip(f"{name} needs an optional extra: {exc}")


def test_every_1x_path_has_a_shim():
    # 109 modules in the approved table, minus core_service.run_pipeline
    # (removed) and dataprep_service.transforms.setup (Cython build script).
    assert (len(MODULES), len(PACKAGES), len(SPLIT)) == (94, 10, 3)
    assert sorted(SPLIT) == [
        "godml.core_service",
        "godml.monitoring_service",
        "godml.utils",
    ]


def test_warning_is_a_deprecation_warning():
    assert issubclass(GoDMLDeprecationWarning, DeprecationWarning)


@pytest.mark.parametrize("old, new", MODULES)
def test_module_shim_warns_and_resolves_to_the_new_module(old, new):
    target = import_or_skip(new)
    with pytest.warns(GoDMLDeprecationWarning, match=re.escape(f"'{old}'")) as record:
        shim = fresh_import(old)
    assert shim is target
    assert new in str(record[-1].message)


@pytest.mark.parametrize("old, new", PACKAGES)
def test_package_shim_reexports_the_new_package(old, new):
    target = import_or_skip(new)
    with pytest.warns(GoDMLDeprecationWarning, match=re.escape(f"'{old}'")):
        shim = fresh_import(old)
    assert shim is not target  # a real package: submodules load only once
    public = getattr(target, "__all__", None) or [
        n for n in vars(target) if not n.startswith("_")
    ]
    for name in public:
        assert getattr(shim, name) is getattr(target, name)


@pytest.mark.parametrize("old", SPLIT)
def test_split_package_shim_warns(old):
    with pytest.warns(GoDMLDeprecationWarning, match="moved to the pillars"):
        fresh_import(old)


def test_warning_points_at_the_importing_code():
    sys.modules.pop("godml.utils.serving", None)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        import godml.utils.serving  # noqa: F401  (a plain import statement)
    assert record and all(Path(w.filename) == Path(__file__) for w in record)


def test_warning_points_at_the_caller_of_import_module():
    for name in ("godml.compliance_service.pci_dss", "godml.compliance_service"):
        sys.modules.pop(name, None)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        importlib.import_module("godml.compliance_service.pci_dss")
    assert len(record) == 2  # the package shim and the module shim
    assert all(Path(w.filename) == Path(__file__) for w in record)


def test_mock_patch_on_an_old_path_reaches_the_new_module(monkeypatch):
    with pytest.warns(GoDMLDeprecationWarning):
        old = fresh_import("godml.compliance_service.pii_detector")
    new = importlib.import_module("godml.govern.compliance.pii_detector")
    monkeypatch.setattr(old, "_GODML_SHIM_PROBE", 1, raising=False)
    assert new._GODML_SHIM_PROBE == 1


@pytest.mark.parametrize(
    "old, new",
    [
        ("godml.model_service.model_loader", "godml.serve.model_loader"),
        ("godml.monitoring_service.thresholds", "godml.govern.thresholds"),
        ("godml.utils.dtypes", "godml.core.dtypes"),
        (
            "godml.dataprep_service.recipe_executor",
            "godml.train.dataprep.recipe_executor",
        ),
        ("godml.core_service.executors", "godml.train.executors"),
        ("godml.core_service.engine", "godml.core.engine"),
        ("godml.utils.scaffold", "godml.tools.scaffold"),
        (
            "godml.dataprep_service.lineage.openlineage_emitter",
            "godml.observe.lineage.openlineage_emitter",
        ),
    ],
)
def test_approved_mapping_adjustments(old, new):
    assert (old, new) in MODULES


def test_run_pipeline_was_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("godml.core_service.run_pipeline")
    assert not (PACKAGE / "train" / "run_pipeline.py").exists()


def test_godml_itself_never_imports_a_1x_path():
    old_names = [old for _, old, _ in SHIMS]
    pattern = re.compile(
        r"\b("
        + "|".join(re.escape(n) for n in sorted(old_names, key=len, reverse=True))
        + r")\b(?![\w])"
    )
    shim_files = {
        path
        for path in PACKAGE.rglob("*.py")
        if "godml.core.deprecation import" in path.read_text(encoding="utf-8")
    }
    offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if path in shim_files or path.name == "deprecation.py":
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert offenders == []


def test_vertex_is_a_documented_stub():
    vertex = importlib.import_module("godml.train.providers.vertex")
    assert "NOT IMPLEMENTED" in vertex.__doc__
    assert [n for n in vars(vertex) if not n.startswith("_")] == []
