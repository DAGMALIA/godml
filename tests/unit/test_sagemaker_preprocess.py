# test_sagemaker_preprocess.py
"""
F1-04: the SageMaker preprocessing script called a non-existent API
(`ComplianceRegistry.get`), ignored the policy, and turned any failure into a
warning, so training received unprocessed PII. The stock sklearn image does
not ship godml, so in practice compliance was always skipped.
"""

import importlib
import sys

import pandas as pd
import pytest

from godml.govern.compliance.errors import ComplianceError
from godml.govern.compliance.pci_dss import PciDssCompliance
from godml.core.dtypes import is_text_like

SCRIPT = "godml.train.providers.sagemaker.scripts.preprocess"


def load_script(monkeypatch, *, without=()):
    """Import the script fresh, optionally hiding godml modules (as in the image)."""
    for module in without:
        monkeypatch.setitem(sys.modules, module, None)
    monkeypatch.delitem(sys.modules, SCRIPT, raising=False)
    return importlib.import_module(SCRIPT)


@pytest.fixture
def script(monkeypatch):
    return load_script(monkeypatch)


class TestCompliance:
    def test_policy_is_applied(self, script, pii_dataframe):
        out = script.apply_compliance(pii_dataframe, "pci-dss", "drop_sensitive")
        assert "card_number" not in out.columns

    def test_engine_failure_aborts(self, script, pii_dataframe, monkeypatch):
        def boom(self, df):
            raise RuntimeError("detector crashed")

        monkeypatch.setattr(PciDssCompliance, "apply", boom)
        with pytest.raises(ComplianceError):
            script.apply_compliance(pii_dataframe, "pci-dss", "mask_sensitive")

    def test_unsupported_standard_aborts(self, script, pii_dataframe):
        with pytest.raises(ComplianceError, match="never protected"):
            script.apply_compliance(pii_dataframe, "gdpr", "mask_sensitive")

    def test_missing_godml_in_image_aborts(self, monkeypatch, pii_dataframe):
        script = load_script(monkeypatch, without=["godml.govern.preprocessor"])
        with pytest.raises(RuntimeError, match="godml is not installed"):
            script.apply_compliance(pii_dataframe, "pci-dss", "mask_sensitive")

    def test_no_compliance_returns_input(self, script, pii_dataframe):
        assert script.apply_compliance(pii_dataframe, "", "mask_sensitive") is (
            pii_dataframe
        )


class TestEncoding:
    def test_text_and_category_columns_are_encoded(self, script):
        df = pd.DataFrame(
            {
                "obj": pd.Series(["a", "b", "a"], dtype=object),
                "txt": pd.Series(["x", "y", "x"], dtype="string"),
                "cat": pd.Series(["u", "v", "u"], dtype="category"),
                "num": [1.0, 2.0, 3.0],
                "target": ["yes", "no", "yes"],
            }
        )
        out = script.encode_categoricals(df, "target")
        for col in ("obj", "txt", "cat", "num"):
            assert pd.api.types.is_numeric_dtype(out[col]), col
        assert list(out["target"]) == ["yes", "no", "yes"]

    def test_fallback_matches_shared_helper(self, monkeypatch):
        """Without godml in the image the script uses its own copy of the helper."""
        script = load_script(monkeypatch, without=["godml.core.dtypes"])
        assert script.is_text_like is not is_text_like
        samples = [
            pd.Series(["a"], dtype=object),
            pd.Series(["a"], dtype="string"),
            pd.Series(["a"], dtype="category"),
            pd.Series([1]),
            pd.Series([1.0]),
            pd.Series([True]),
        ]
        for s in samples:
            assert script.is_text_like(s.dtype) is is_text_like(s.dtype), s.dtype


def test_import_has_no_side_effects(monkeypatch, tmp_path):
    """Importing must not create /opt/ml dirs or read input (it used to run on import)."""
    created = []
    monkeypatch.setattr("os.makedirs", lambda *a, **k: created.append(a))
    load_script(monkeypatch)
    assert created == []
