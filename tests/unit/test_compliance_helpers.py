"""Tests for compliance_registry, validation_helpers."""
from __future__ import annotations

import pytest


class TestComplianceRegistry:
    def test_get_pci_dss(self):
        from godml.compliance_service.compliance_registry import ComplianceRegistry
        instance = ComplianceRegistry.get_compliance("pci-dss")
        assert instance is not None

    def test_get_pci_dss_case_insensitive(self):
        from godml.compliance_service.compliance_registry import ComplianceRegistry
        instance = ComplianceRegistry.get_compliance("PCI-DSS")
        assert instance is not None

    def test_unknown_compliance_raises(self):
        from godml.compliance_service.compliance_registry import ComplianceRegistry
        with pytest.raises(ValueError, match="no registrada"):
            ComplianceRegistry.get_compliance("gdpr")

    def test_list_supported(self):
        from godml.compliance_service.compliance_registry import ComplianceRegistry
        supported = ComplianceRegistry.list_supported()
        assert "pci-dss" in supported

    def test_register_custom(self):
        from godml.compliance_service.compliance_registry import ComplianceRegistry
        from godml.compliance_service.base_compliance import BaseCompliance
        import pandas as pd

        class DummyCompliance(BaseCompliance):
            def apply(self, df: pd.DataFrame) -> pd.DataFrame:
                return df

        ComplianceRegistry.register("dummy", DummyCompliance)
        instance = ComplianceRegistry.get_compliance("dummy")
        assert isinstance(instance, DummyCompliance)


class TestValidationHelpers:
    def _make_pipeline(self, **overrides):
        from godml.config_service.schema import (
            PipelineDefinition, DatasetConfig, ModelConfig, Hyperparameters, Metric, Governance, DeployConfig
        )
        defaults = dict(
            name="test",
            version="1.0.0",
            provider="mlflow",
            dataset=DatasetConfig(uri="./data.csv", hash="abc123"),
            model=ModelConfig(type="xgboost", source="core", hyperparameters=Hyperparameters()),
            metrics=[Metric(name="auc", threshold=0.80)],
            governance=Governance(owner="owner@test.com", tags=[{"compliance": "pci-dss"}]),
            deploy=DeployConfig(realtime=False, batch_output="./out.csv"),
        )
        defaults.update(overrides)
        return PipelineDefinition(**defaults)

    def test_is_valid_owner_true(self):
        from godml.compliance_service.validation_helpers import is_valid_owner
        assert is_valid_owner("team@company.com") is True

    def test_is_valid_owner_empty_false(self):
        from godml.compliance_service.validation_helpers import is_valid_owner
        assert not is_valid_owner("")
        assert not is_valid_owner(None)

    def test_is_valid_hash_true(self):
        from godml.compliance_service.validation_helpers import is_valid_hash
        assert is_valid_hash("abc123") is True

    def test_is_valid_hash_auto_false(self):
        from godml.compliance_service.validation_helpers import is_valid_hash
        assert not is_valid_hash("auto")

    def test_validate_metrics_valid(self):
        from godml.compliance_service.validation_helpers import validate_metrics
        from godml.config_service.schema import Metric
        errors = validate_metrics([Metric(name="auc", threshold=0.85)])
        assert errors == []

    def test_validate_metrics_out_of_range(self):
        from godml.compliance_service.validation_helpers import validate_metrics
        from godml.config_service.schema import Metric
        errors = validate_metrics([Metric(name="auc", threshold=1.5)])
        assert len(errors) == 1

    def test_is_valid_deploy_config_batch(self):
        from godml.compliance_service.validation_helpers import is_valid_deploy_config
        pipe = self._make_pipeline()
        assert is_valid_deploy_config(pipe) is True

    def test_has_compliance_tag_true(self):
        from godml.compliance_service.validation_helpers import has_compliance_tag
        tags = [{"compliance": "pci-dss"}, {"env": "prod"}]
        assert has_compliance_tag(tags) is True

    def test_has_compliance_tag_false(self):
        from godml.compliance_service.validation_helpers import has_compliance_tag
        tags = [{"env": "prod"}]
        assert has_compliance_tag(tags) is False

    def test_validate_pipeline_clean(self):
        from godml.compliance_service.validation_helpers import validate_pipeline
        pipe = self._make_pipeline()
        warnings = validate_pipeline(pipe)
        assert isinstance(warnings, list)

    def test_validate_pipeline_missing_owner_raises(self):
        from godml.compliance_service.validation_helpers import validate_pipeline, ValidationError
        from godml.config_service.schema import Governance
        pipe = self._make_pipeline(governance=Governance(owner="", tags=[{"compliance": "pci-dss"}]))
        with pytest.raises(ValidationError):
            validate_pipeline(pipe)

    def test_validate_pipeline_auto_hash_warns(self):
        from godml.compliance_service.validation_helpers import validate_pipeline
        from godml.config_service.schema import DatasetConfig
        pipe = self._make_pipeline(dataset=DatasetConfig(uri="./data.csv", hash="auto"))
        warnings = validate_pipeline(pipe)
        assert any("hash" in w.lower() or "auto" in w.lower() for w in warnings)
