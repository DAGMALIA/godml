import os

import pytest
import yaml

from godml.config_service.schema import PipelineDefinition
from godml.core_service.parser import load_pipeline
from godml.monitoring_service.logger import ConfigurationError, SecurityError


class TestLoadPipeline:
    def test_yaml_to_pipeline_definition(self, temp_yaml):
        config = load_pipeline(temp_yaml)
        assert isinstance(config, PipelineDefinition)
        assert config.name == "test-pipeline"
        assert config.dataset.uri.endswith("test.csv")
        assert config.model.type == "xgboost"
        assert config.deploy.batch_output.endswith("preds.csv")

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises((FileNotFoundError, SecurityError)):
            load_pipeline(str(tmp_path / "does_not_exist.yml"))

    def test_wrong_extension_rejected(self, tmp_path):
        f = tmp_path / "config.json"
        f.write_text("{}")
        with pytest.raises(SecurityError):
            load_pipeline(str(f))

    def test_empty_yaml_raises(self, tmp_path):
        f = tmp_path / "empty.yml"
        f.write_text("")
        with pytest.raises(ConfigurationError):
            load_pipeline(str(f))

    def test_invalid_pipeline_definition_raises(self, tmp_path):
        f = tmp_path / "bad.yml"
        f.write_text(yaml.dump({"name": "incomplete-pipeline"}))
        with pytest.raises(ConfigurationError):
            load_pipeline(str(f))


class TestEnvVarResolution:
    """core_service.parser is the loader `godml run` actually uses — env var
    interpolation must work here, not only in the separate config_service.loader path."""

    def test_env_var_resolved(self, tmp_path, monkeypatch, minimal_pipeline_config):
        monkeypatch.setenv("GODML_TEST_OWNER", "owner@resolved.com")
        config_dict = dict(minimal_pipeline_config)
        config_dict["governance"] = {"owner": "${GODML_TEST_OWNER}"}
        f = tmp_path / "godml.yml"
        f.write_text(yaml.dump(config_dict))

        config = load_pipeline(str(f))
        assert config.governance.owner == "owner@resolved.com"

    def test_env_var_uses_default_when_missing(self, tmp_path, minimal_pipeline_config):
        os.environ.pop("GODML_TEST_MISSING_XYZ", None)
        config_dict = dict(minimal_pipeline_config)
        config_dict["governance"] = {"owner": "${GODML_TEST_MISSING_XYZ:fallback@company.com}"}
        f = tmp_path / "godml.yml"
        f.write_text(yaml.dump(config_dict))

        config = load_pipeline(str(f))
        assert config.governance.owner == "fallback@company.com"

    def test_env_var_empty_default_resolves(self, tmp_path, monkeypatch, minimal_pipeline_config):
        # Regression test: ${VAR:} (empty default) used to fail to match at all,
        # leaving the literal "${VAR:}" string even when the env var was set.
        monkeypatch.setenv("GODML_TEST_KMS", "real-kms-key")
        config_dict = dict(minimal_pipeline_config)
        config_dict["aws"] = {
            "role_arn": "arn:aws:iam::123:role/x",
            "s3_bucket": "bucket",
            "kms_key_id": "${GODML_TEST_KMS:}",
        }
        f = tmp_path / "godml.yml"
        f.write_text(yaml.dump(config_dict))

        config = load_pipeline(str(f))
        assert config.aws.kms_key_id == "real-kms-key"


class TestRemoteUriPreserved:
    """normalize_path() must not mangle non-local URIs (s3://, gs://, etc.) —
    it used to turn 's3://bucket/x' into a garbled local Windows path."""

    def test_s3_dataset_uri_untouched(self, tmp_path, minimal_pipeline_config):
        config_dict = dict(minimal_pipeline_config)
        config_dict["dataset"]["uri"] = "s3://my-bucket/data/train.csv"
        f = tmp_path / "godml.yml"
        f.write_text(yaml.dump(config_dict))

        config = load_pipeline(str(f))
        assert config.dataset.uri == "s3://my-bucket/data/train.csv"

    def test_s3_batch_output_untouched(self, tmp_path, minimal_pipeline_config):
        config_dict = dict(minimal_pipeline_config)
        config_dict["deploy"]["batch_output"] = "s3://my-bucket/output/preds.csv"
        f = tmp_path / "godml.yml"
        f.write_text(yaml.dump(config_dict))

        config = load_pipeline(str(f))
        assert config.deploy.batch_output == "s3://my-bucket/output/preds.csv"

    def test_local_dataset_uri_still_normalized(self, tmp_path, minimal_pipeline_config):
        config_dict = dict(minimal_pipeline_config)
        config_dict["dataset"]["uri"] = "./data/train.csv"
        f = tmp_path / "godml.yml"
        f.write_text(yaml.dump(config_dict))

        config = load_pipeline(str(f))
        # normalize_path resolves it to an absolute path — no longer the raw relative string.
        assert config.dataset.uri != "./data/train.csv"
        assert config.dataset.uri.endswith("train.csv")
