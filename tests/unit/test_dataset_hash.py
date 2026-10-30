# test_dataset_hash.py
"""
F1-05: a pinned `dataset.hash` was only checked for being non-"auto"; `godml
run` never compared it with the file, so training silently used whatever data
was at dataset.uri.
"""

import pandas as pd
import pytest

import godml.providers.mlflow as mlflow_provider
from godml.compliance_service.dataset_integrity import verify_dataset_hash
from godml.compliance_service.errors import DatasetIntegrityError
from godml.config_service.schema import PipelineDefinition
from godml.utils.hash import calculate_file_hash


@pytest.fixture
def dataset(tmp_path):
    path = tmp_path / "data.csv"
    pd.DataFrame({"x": range(10), "y": [0, 1] * 5}).to_csv(path, index=False)
    return path


class TestVerifyDatasetHash:
    def test_matching_hash_passes(self, dataset):
        verify_dataset_hash(str(dataset), calculate_file_hash(str(dataset)))

    @pytest.mark.parametrize("fmt", [str.upper, lambda h: f"sha256:{h}", str.strip])
    def test_accepted_formats(self, dataset, fmt):
        verify_dataset_hash(str(dataset), fmt(calculate_file_hash(str(dataset))))

    def test_mismatch_raises_with_both_hashes(self, dataset):
        pinned = "0" * 64
        with pytest.raises(DatasetIntegrityError) as excinfo:
            verify_dataset_hash(str(dataset), pinned)
        message = str(excinfo.value)
        assert pinned in message
        assert calculate_file_hash(str(dataset)) in message
        assert "godml calc-hash" in message

    @pytest.mark.parametrize("pinned", [None, "", "auto", "AUTO"])
    def test_not_pinned_is_skipped(self, dataset, pinned):
        verify_dataset_hash(str(dataset), pinned)

    def test_missing_file_with_pinned_hash_raises(self, tmp_path):
        with pytest.raises(DatasetIntegrityError):
            verify_dataset_hash(str(tmp_path / "missing.csv"), "0" * 64)


class TestGodmlRun:
    """MLflowExecutor.run must stop before training when the pinned hash differs."""

    @pytest.fixture
    def run_until_training(
        self, dataset, tmp_path, monkeypatch, minimal_pipeline_config
    ):
        monkeypatch.chdir(tmp_path)

        class TrainingReached(Exception):
            pass

        def reached(*args, **kwargs):
            raise TrainingReached

        monkeypatch.setattr(mlflow_provider, "train_test_split", reached)

        def run(pinned_hash):
            config = dict(minimal_pipeline_config)
            config["dataset"] = {
                "uri": str(dataset),
                "hash": pinned_hash,
                "target": "y",
            }
            executor = mlflow_provider.MLflowExecutor(
                tracking_uri="sqlite:///mlflow.db"
            )
            executor.run(PipelineDefinition(**config))

        return run, TrainingReached

    def test_mismatch_aborts_before_training(self, run_until_training):
        run, _ = run_until_training
        with pytest.raises(DatasetIntegrityError):
            run("f" * 64)

    def test_matching_hash_reaches_training(self, run_until_training, dataset):
        run, training_reached = run_until_training
        with pytest.raises(training_reached):
            run(calculate_file_hash(str(dataset)))

    def test_auto_reaches_training(self, run_until_training):
        run, training_reached = run_until_training
        with pytest.raises(training_reached):
            run("auto")


class TestSageMaker:
    """S3 data cannot be hashed locally yet (F3-03): say so instead of implying it was checked."""

    def run_validate(self, monkeypatch, minimal_pipeline_config, pinned_hash):
        import godml.providers.sagemaker.executor as sm

        warnings_logged: list[str] = []
        monkeypatch.setattr(
            sm.logger, "warning", lambda msg, *a, **k: warnings_logged.append(str(msg))
        )
        # Stop right after the config-only checks; AWS libs are not needed.
        monkeypatch.setattr(sm, "_require_aws", lambda: (_ for _ in ()).throw(StopAt()))

        config = dict(minimal_pipeline_config)
        config["provider"] = "sagemaker"
        config["dataset"] = {
            "uri": "s3://bucket/d.csv",
            "hash": pinned_hash,
            "target": "y",
        }
        with pytest.raises(StopAt):
            sm.SageMakerExecutor().validate(PipelineDefinition(**config))
        return warnings_logged

    def test_pinned_hash_warns_not_verified(self, monkeypatch, minimal_pipeline_config):
        logged = self.run_validate(monkeypatch, minimal_pipeline_config, "a" * 64)
        assert any("dataset.hash" in m and "not verified" in m for m in logged), logged

    def test_auto_hash_does_not_warn(self, monkeypatch, minimal_pipeline_config):
        logged = self.run_validate(monkeypatch, minimal_pipeline_config, "auto")
        assert not any("dataset.hash" in m for m in logged), logged


class StopAt(Exception):
    pass
