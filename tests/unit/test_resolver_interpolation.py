# test_resolver_interpolation.py
"""
F1-09: the resolver did not recurse into dicts/lists inside lists (so
`${VAR}` in `metrics: [{...}]` or `governance.tags` stayed literal) and
replaced a whole string by the variable when it only contained one
(`"s3://${BUCKET}/data"` became just the bucket name).
"""

import pytest

from godml.core.config.resolver import resolve_env_variables
from godml.core.logger import ConfigurationError


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("BUCKET", "my-bucket")
    monkeypatch.setenv("TEAM", "revenue")
    monkeypatch.delenv("UNSET_VAR_F109", raising=False)


def test_dicts_inside_lists_are_resolved():
    config = {"governance": {"tags": [{"team": "${TEAM}"}, {"env": "dev"}]}}
    assert resolve_env_variables(config)["governance"]["tags"] == [
        {"team": "revenue"},
        {"env": "dev"},
    ]


def test_nested_lists_are_resolved():
    assert resolve_env_variables({"x": [["${TEAM}"], [1, "${BUCKET}"]]}) == {
        "x": [["revenue"], [1, "my-bucket"]]
    }


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("s3://${BUCKET}/data.csv", "s3://my-bucket/data.csv"),
        ("prefix-${TEAM}", "prefix-revenue"),
        ("${TEAM}-${BUCKET}", "revenue-my-bucket"),
        ("./data/${UNSET_VAR_F109:train}.csv", "./data/train.csv"),
        ("${UNSET_VAR_F109:}x", "x"),
        ("no variables here", "no variables here"),
    ],
)
def test_partial_interpolation(raw, expected):
    assert resolve_env_variables({"k": raw})["k"] == expected


def test_partial_unset_without_default_fails():
    with pytest.raises(ConfigurationError, match="UNSET_VAR_F109"):
        resolve_env_variables({"uri": "./data/${UNSET_VAR_F109}.csv"})


def test_whole_value_unset_without_default_stays_none():
    """1.x behavior kept: a value that is only `${VAR}` becomes None."""
    assert resolve_env_variables({"k": "${UNSET_VAR_F109}"})["k"] is None


def test_input_is_not_mutated():
    config = {"tags": [{"team": "${TEAM}"}]}
    resolve_env_variables(config)
    assert config == {"tags": [{"team": "${TEAM}"}]}


class TestThroughGodmlRunLoader:
    """core_service.parser.load_pipeline is what `godml run` uses."""

    def write(self, tmp_path, minimal_pipeline_config, **dataset):
        import yaml

        config = dict(minimal_pipeline_config)
        config["dataset"] = {"hash": "auto", "target": "y", **dataset}
        config["governance"] = {"owner": "o@x.com", "tags": [{"team": "${TEAM}"}]}
        path = tmp_path / "godml.yml"
        path.write_text(yaml.safe_dump(config))
        return str(path)

    def test_yaml_interpolation(self, tmp_path, monkeypatch, minimal_pipeline_config):
        from godml.core.parser import load_pipeline

        monkeypatch.chdir(tmp_path)
        pipeline = load_pipeline(
            self.write(tmp_path, minimal_pipeline_config, uri="s3://${BUCKET}/d.csv")
        )
        assert pipeline.dataset.uri == "s3://my-bucket/d.csv"
        assert pipeline.governance.tags == [{"team": "revenue"}]

    def test_yaml_unset_partial_variable(
        self, tmp_path, monkeypatch, minimal_pipeline_config
    ):
        from godml.core.parser import load_pipeline

        monkeypatch.chdir(tmp_path)
        path = self.write(
            tmp_path, minimal_pipeline_config, uri="s3://${UNSET_VAR_F109}/d.csv"
        )
        with pytest.raises(ConfigurationError, match="UNSET_VAR_F109"):
            load_pipeline(path)
