# test_sagemaker_evaluate.py
"""
F1-18: evaluate.py ran everything at import (os.makedirs under /opt/ml, model
extraction, metrics), and its tarball filter used `startswith`, so a member
like ../model_evil/x escaped into a sibling directory of the model dir.
"""

import importlib
import io
import json
import sys
import tarfile

import joblib
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

SCRIPT = "godml.train.providers.sagemaker.scripts.evaluate"


@pytest.fixture
def made_dirs(monkeypatch):
    """Record os.makedirs during import so a module-level call cannot touch disk."""
    calls: list[tuple] = []
    monkeypatch.setattr("os.makedirs", lambda *a, **k: calls.append(a))
    return calls


@pytest.fixture
def script(monkeypatch, made_dirs):
    monkeypatch.delitem(sys.modules, SCRIPT, raising=False)
    module = importlib.import_module(SCRIPT)
    monkeypatch.undo()  # real os.makedirs for the test body
    return module


def test_import_has_no_side_effects(script, made_dirs):
    assert made_dirs == []


def add_member(tar: tarfile.TarFile, name: str, data: bytes = b"x", **attrs) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    for key, value in attrs.items():
        setattr(info, key, value)
    tar.addfile(info, io.BytesIO(data))


def make_archive(path, members) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, attrs in members:
            add_member(tar, name, **attrs)


class TestSafeExtraction:
    @pytest.fixture
    def model_dir(self, tmp_path):
        d = tmp_path / "model"
        d.mkdir()
        return d

    def test_regular_members_are_extracted(self, script, model_dir):
        make_archive(model_dir / "m.tar.gz", [("model.joblib", {}), ("sub/a.txt", {})])
        script.extract_model_archives(str(model_dir))
        assert (model_dir / "model.joblib").is_file()
        assert (model_dir / "sub" / "a.txt").is_file()

    @pytest.mark.parametrize(
        "name",
        [
            "../model_evil/x.txt",  # sibling dir sharing the prefix: passed `startswith`
            "../escape.txt",
            "/abs/escape.txt",
        ],
    )
    def test_traversal_is_rejected(self, script, model_dir, tmp_path, name):
        make_archive(model_dir / "m.tar.gz", [(name, {})])
        with pytest.raises(ValueError, match="Unsafe"):
            script.extract_model_archives(str(model_dir))
        assert not (tmp_path / "model_evil").exists()
        assert not (tmp_path / "escape.txt").exists()

    @pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE])
    def test_links_are_rejected(self, script, model_dir, kind):
        make_archive(
            model_dir / "m.tar.gz",
            [("link", {"type": kind, "linkname": "../../etc/passwd", "size": 0})],
        )
        with pytest.raises(ValueError, match="Unsafe"):
            script.extract_model_archives(str(model_dir))


def test_main_writes_evaluation(script, tmp_path, monkeypatch):
    model_dir, test_dir, out_dir = (tmp_path / d for d in ("model", "test", "eval"))
    model_dir.mkdir()
    test_dir.mkdir()

    df = pd.DataFrame(
        {"x": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0], "label": [0, 0, 0, 1, 1, 1]}
    )
    model = LogisticRegression().fit(df[["x"]], df["label"])
    joblib.dump(model, tmp_path / "model.joblib")
    with tarfile.open(model_dir / "model.tar.gz", "w:gz") as tar:
        tar.add(tmp_path / "model.joblib", arcname="model.joblib")
    df.to_csv(test_dir / "test.csv", index=False)

    monkeypatch.setenv("GODML_TARGET_COL", "label")
    script.main(model_dir=str(model_dir), test_dir=str(test_dir), out_dir=str(out_dir))

    metrics = json.loads((out_dir / "evaluation.json").read_text())
    assert metrics["accuracy"] == 1.0
    assert "auc" in metrics
