# test_compliance_fail_closed.py
"""
F1-01: when compliance is requested and cannot be applied, the pipeline must
abort. It used to log the error and continue with the raw (PII) DataFrame.
"""

import sys

import pandas as pd
import pytest

from godml.govern.compliance.pci_dss import PciDssCompliance
from godml.core.config.schema import PipelineDefinition
from godml.govern.pipeline_runner import run_pipeline_preprocessing
from godml.govern.preprocessor import ComplianceEngine
from godml.train.dataprep.recipe_executor import _apply_compliance
from godml.govern.compliance.errors import ComplianceError


def assert_unsupported_message(message: str, standard: str) -> None:
    """The error must tell users their data was never protected and how to fix it."""
    assert f"'{standard}'" in message
    assert "never protected" in message
    assert "pci-dss" in message
    assert "remove" in message
    assert "CHANGELOG" in message and "1.4.0" in message


@pytest.fixture
def broken_pci(monkeypatch):
    def boom(self, df):
        raise RuntimeError("detector crashed")

    monkeypatch.setattr(PciDssCompliance, "apply", boom)


@pytest.fixture
def compliance_pipeline(minimal_pipeline_config, tmp_path):
    config = dict(minimal_pipeline_config)
    config["dataset"] = {
        "uri": str(tmp_path / "data.csv"),
        "hash": "auto",
        "target": "y",
    }
    config["governance"] = {"owner": "test@company.com", "compliance": "pci-dss"}
    return PipelineDefinition(**config)


class TestComplianceEngine:
    def test_engine_error_raises(self, pii_dataframe, broken_pci):
        with pytest.raises(ComplianceError, match="detector crashed"):
            ComplianceEngine.apply(pii_dataframe, "pci-dss", "mask_sensitive")

    def test_unsupported_standard_raises(self, pii_dataframe):
        with pytest.raises(ComplianceError) as excinfo:
            ComplianceEngine.apply(pii_dataframe, "gdpr", "mask_sensitive")
        assert_unsupported_message(str(excinfo.value), "gdpr")

    def test_import_failure_raises(self, pii_dataframe, monkeypatch):
        monkeypatch.setitem(sys.modules, "godml.govern.compliance.pci_dss", None)
        with pytest.raises(ComplianceError):
            ComplianceEngine.apply(pii_dataframe, "pci-dss", "mask_sensitive")

    def test_lineage_failure_does_not_block_compliance(
        self, pii_dataframe, monkeypatch
    ):
        import godml.govern.preprocessor as preprocessor

        def no_lineage(*args, **kwargs):
            raise OSError("lineage backend down")

        monkeypatch.setattr(preprocessor, "emit", no_lineage)
        out = ComplianceEngine.apply(pii_dataframe, "pci-dss", "drop_sensitive")
        assert "card_number" not in out.columns

    def test_no_compliance_requested_returns_input(self, pii_dataframe):
        assert ComplianceEngine.apply(pii_dataframe, None) is pii_dataframe


class TestPipelinePreprocessing:
    def test_compliance_error_propagates(
        self, compliance_pipeline, pii_dataframe, broken_pci
    ):
        with pytest.raises(ComplianceError):
            run_pipeline_preprocessing(compliance_pipeline, pii_dataframe)


class TestDataprepHook:
    def test_unsupported_standard_raises(self, pii_dataframe):
        with pytest.raises(ComplianceError) as excinfo:
            _apply_compliance(pii_dataframe, {"compliance": "gdpr"})
        assert_unsupported_message(str(excinfo.value), "gdpr")


class TestMLflowExecutor:
    def test_compliance_failure_aborts_before_training(
        self, compliance_pipeline, pii_dataframe, broken_pci, monkeypatch, tmp_path
    ):
        import godml.train.providers.mlflow as mlflow_provider

        df = pii_dataframe.assign(y=[0, 1, 0])
        df.to_csv(compliance_pipeline.dataset.uri, index=False)
        monkeypatch.chdir(tmp_path)

        def training_started(*args, **kwargs):
            pytest.fail("training ran on data that did not pass compliance")

        monkeypatch.setattr(mlflow_provider, "train_test_split", training_started)

        with pytest.raises(ComplianceError):
            mlflow_provider.MLflowExecutor().run(compliance_pipeline)


def test_compliant_data_still_flows(compliance_pipeline, pii_dataframe):
    out = run_pipeline_preprocessing(compliance_pipeline, pii_dataframe)
    assert isinstance(out, pd.DataFrame)
    assert list(out["card_number"]) != list(pii_dataframe["card_number"])
