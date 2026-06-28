import pytest
import os
import yaml
from godml.config_service.resolver import resolve_env_variables
from godml.config_service.schema import (
    PipelineDefinition, DatasetConfig, ModelConfig,
    Governance, DeployConfig, Metric, Hyperparameters,
)
from godml.config_service.loader import load_config
from godml.monitoring_service.logger import ConfigurationError


class TestResolver:
    def test_plain_string_unchanged(self):
        result = resolve_env_variables({"key": "plain_value"})
        assert result["key"] == "plain_value"

    def test_resolves_env_var(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "hello")
        result = resolve_env_variables({"key": "${MY_VAR}"})
        assert result["key"] == "hello"

    def test_uses_default_when_var_missing(self):
        os.environ.pop("MISSING_VAR_XYZ", None)
        result = resolve_env_variables({"key": "${MISSING_VAR_XYZ:fallback}"})
        assert result["key"] == "fallback"

    def test_nested_dict_resolved(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "localhost")
        result = resolve_env_variables({"db": {"host": "${DB_HOST}"}})
        assert result["db"]["host"] == "localhost"

    def test_list_items_resolved(self, monkeypatch):
        monkeypatch.setenv("ITEM_VAL", "resolved")
        result = resolve_env_variables({"items": ["${ITEM_VAL}", "static"]})
        assert result["items"][0] == "resolved"
        assert result["items"][1] == "static"

    def test_non_string_values_pass_through(self):
        result = resolve_env_variables({"num": 42, "flag": True, "nothing": None})
        assert result["num"] == 42
        assert result["flag"] is True
        assert result["nothing"] is None

    def test_empty_dict(self):
        result = resolve_env_variables({})
        assert result == {}


class TestPipelineDefinitionSchema:
    def test_valid_minimal_config(self, minimal_pipeline_config):
        pipe = PipelineDefinition(**minimal_pipeline_config)
        assert pipe.name == "test-pipeline"
        assert pipe.version == "1.0.0"
        assert pipe.provider == "mlflow"

    def test_missing_name_raises(self, minimal_pipeline_config):
        del minimal_pipeline_config["name"]
        with pytest.raises(Exception):
            PipelineDefinition(**minimal_pipeline_config)

    def test_missing_provider_raises(self, minimal_pipeline_config):
        del minimal_pipeline_config["provider"]
        with pytest.raises(Exception):
            PipelineDefinition(**minimal_pipeline_config)

    def test_governance_policy_defaults_to_mask(self, minimal_pipeline_config):
        pipe = PipelineDefinition(**minimal_pipeline_config)
        assert pipe.governance.policy == "mask_sensitive"

    def test_governance_tags_defaults_to_empty(self, minimal_pipeline_config):
        pipe = PipelineDefinition(**minimal_pipeline_config)
        assert pipe.governance.tags == []

    def test_hyperparameters_partial(self, minimal_pipeline_config):
        pipe = PipelineDefinition(**minimal_pipeline_config)
        assert pipe.model.hyperparameters.max_depth == 3
        assert pipe.model.hyperparameters.eta is None
        assert pipe.model.hyperparameters.n_estimators is None

    def test_deploy_realtime_false(self, minimal_pipeline_config):
        pipe = PipelineDefinition(**minimal_pipeline_config)
        assert pipe.deploy.realtime is False

    def test_dataset_uri(self, minimal_pipeline_config):
        pipe = PipelineDefinition(**minimal_pipeline_config)
        assert pipe.dataset.uri == "./data/test.csv"

    def test_metrics_list(self, minimal_pipeline_config):
        pipe = PipelineDefinition(**minimal_pipeline_config)
        assert len(pipe.metrics) == 1
        assert pipe.metrics[0].name == "auc"
        assert pipe.metrics[0].threshold == 0.7

    def test_description_optional(self, minimal_pipeline_config):
        pipe = PipelineDefinition(**minimal_pipeline_config)
        assert pipe.description is None


class TestLoadConfig:
    def test_loads_valid_yaml(self, temp_yaml):
        config = load_config(temp_yaml)
        assert isinstance(config, PipelineDefinition)
        assert config.name == "test-pipeline"

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(str(tmp_path / "nonexistent.yml"))

    def test_empty_yaml_raises_config_error(self, tmp_path):
        f = tmp_path / "empty.yml"
        f.write_text("")
        with pytest.raises(ConfigurationError):
            load_config(str(f))

    def test_invalid_yaml_syntax_raises(self, tmp_path):
        f = tmp_path / "bad.yml"
        f.write_text("key: [\n  broken: yaml\n  :")
        with pytest.raises(ConfigurationError):
            load_config(str(f))

    def test_valid_yaml_missing_required_field_raises(self, tmp_path):
        f = tmp_path / "partial.yml"
        f.write_text(yaml.dump({"name": "only-name"}))
        with pytest.raises(ConfigurationError):
            load_config(str(f))

    def test_env_var_resolved_on_load(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PIPE_OWNER", "owner@env.com")
        config_dict = {
            "name": "env-pipe",
            "version": "1.0.0",
            "provider": "mlflow",
            "dataset": {"uri": "./d.csv"},
            "model": {"type": "xgboost", "hyperparameters": {}},
            "metrics": [{"name": "auc", "threshold": 0.7}],
            "governance": {"owner": "${PIPE_OWNER}"},
            "deploy": {"realtime": False, "batch_output": "./out.csv"},
        }
        f = tmp_path / "godml.yml"
        f.write_text(yaml.dump(config_dict))
        config = load_config(str(f))
        assert config.governance.owner == "owner@env.com"
