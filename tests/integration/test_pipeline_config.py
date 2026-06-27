import pytest
import os
import yaml
import pandas as pd
import numpy as np
from godml.config_service.loader import load_config
from godml.config_service.schema import PipelineDefinition
from godml.compliance_service.pci_dss import PciDssCompliance


class TestFullConfigLoadCycle:
    def test_yaml_to_pipeline_definition(self, temp_yaml):
        config = load_config(temp_yaml)
        assert isinstance(config, PipelineDefinition)
        assert config.name == "test-pipeline"
        assert config.version == "1.0.0"
        assert config.provider == "mlflow"
        assert config.dataset.uri == "./data/test.csv"
        assert config.model.type == "xgboost"
        assert config.model.hyperparameters.max_depth == 3
        assert config.deploy.realtime is False
        assert config.deploy.batch_output == "./outputs/preds.csv"

    def test_governance_defaults_applied(self, temp_yaml):
        config = load_config(temp_yaml)
        assert config.governance.owner == "test@company.com"
        assert config.governance.policy == "mask_sensitive"
        assert config.governance.tags == []

    def test_env_var_resolved_in_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PIPELINE_OWNER", "owner@resolved.com")
        monkeypatch.setenv("PIPELINE_ENV", "production")
        config_dict = {
            "name": "env-pipeline",
            "version": "1.0.0",
            "provider": "mlflow",
            "dataset": {"uri": "./data.csv"},
            "model": {"type": "random_forest", "hyperparameters": {}},
            "metrics": [{"name": "f1", "threshold": 0.8}],
            "governance": {
                "owner": "${PIPELINE_OWNER}",
                "tags": [{"env": "${PIPELINE_ENV:staging}"}],
            },
            "deploy": {"realtime": False, "batch_output": "./out.csv"},
        }
        f = tmp_path / "godml.yml"
        f.write_text(yaml.dump(config_dict))
        config = load_config(str(f))
        assert config.governance.owner == "owner@resolved.com"

    def test_env_var_uses_default_when_missing(self, tmp_path):
        os.environ.pop("MISSING_OWNER_XYZ", None)
        config_dict = {
            "name": "default-pipe",
            "version": "1.0.0",
            "provider": "mlflow",
            "dataset": {"uri": "./data.csv"},
            "model": {"type": "xgboost", "hyperparameters": {}},
            "metrics": [{"name": "auc", "threshold": 0.7}],
            "governance": {"owner": "${MISSING_OWNER_XYZ:fallback@company.com}"},
            "deploy": {"realtime": False, "batch_output": "./out.csv"},
        }
        f = tmp_path / "godml.yml"
        f.write_text(yaml.dump(config_dict))
        config = load_config(str(f))
        assert config.governance.owner == "fallback@company.com"


class TestCompliancePipelineIntegration:
    def test_config_policy_drives_compliance(self, temp_yaml, pii_dataframe):
        config = load_config(temp_yaml)
        policy = config.governance.policy
        compliance = PciDssCompliance(policy=policy)
        result = compliance.apply(pii_dataframe)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(pii_dataframe)

    def test_drop_policy_removes_columns(self, tmp_path, pii_dataframe):
        config_dict = {
            "name": "drop-pipe",
            "version": "1.0.0",
            "provider": "mlflow",
            "dataset": {"uri": "./data.csv"},
            "model": {"type": "xgboost", "hyperparameters": {}},
            "metrics": [{"name": "auc", "threshold": 0.7}],
            "governance": {"owner": "owner@test.com", "policy": "drop_sensitive"},
            "deploy": {"realtime": False, "batch_output": "./out.csv"},
        }
        f = tmp_path / "drop.yml"
        f.write_text(yaml.dump(config_dict))
        config = load_config(str(f))
        compliance = PciDssCompliance(policy=config.governance.policy)
        result = compliance.apply(pii_dataframe)
        original_col_count = len(pii_dataframe.columns)
        assert len(result.columns) < original_col_count

    def test_hash_policy_produces_fixed_length_hashes(self, tmp_path, pii_dataframe):
        config_dict = {
            "name": "hash-pipe",
            "version": "1.0.0",
            "provider": "mlflow",
            "dataset": {"uri": "./data.csv"},
            "model": {"type": "xgboost", "hyperparameters": {}},
            "metrics": [{"name": "auc", "threshold": 0.7}],
            "governance": {"owner": "owner@test.com", "policy": "hash_sensitive"},
            "deploy": {"realtime": False, "batch_output": "./out.csv"},
        }
        f = tmp_path / "hash.yml"
        f.write_text(yaml.dump(config_dict))
        config = load_config(str(f))
        compliance = PciDssCompliance(policy=config.governance.policy)
        result = compliance.apply(pii_dataframe)
        for val in result["email"].tolist():
            assert isinstance(val, str)
            assert len(val) == 12


class TestModelIntegration:
    def test_config_model_type_maps_to_notebook_api(self, temp_yaml, binary_dataset):
        from godml.notebook_api import train_model
        config = load_config(temp_yaml)
        ds = binary_dataset
        result = train_model(
            config.model.type,
            ds["X_train"],
            pd.Series(ds["y_train"]),
            hyperparams={"n_estimators": 10},
        )
        assert result.model is not None

    def test_metrics_threshold_from_config(self, temp_yaml):
        config = load_config(temp_yaml)
        assert len(config.metrics) > 0
        for metric in config.metrics:
            assert metric.threshold > 0
            assert metric.threshold <= 1.0
