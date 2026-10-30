# test_spec_v2.py
"""F2-02: spec v2 in Pydantic, unknown keys rejected, JSON Schema published."""

import copy
import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from godml.core.spec import PipelineSpecV2, json_schema

ROOT = Path(__file__).resolve().parents[2]

# The draft in GODML_2_0_PLAN.md (section 1), kept verbatim.
DRAFT = yaml.safe_load(
    """
apiVersion: godml.io/v2
kind: ModelPipeline
metadata:
  name: churn-predictor
  version: 1.4.0
  owner: data-science@company.com
  tags: { team: revenue, env: "${GODML_ENV:dev}" }
spec:
  data:
    uri: ./data/churn.csv
    sha256: auto
    target: churned
  train:
    estimator: xgboost.XGBClassifier
    params: { max_depth: 5, n_estimators: 200 }
    preprocess: { recipe: ./recipes/churn.yaml }
  govern:
    policies: [pci-dss]
    metrics:
      auc: ">= 0.80"
      log_loss: "<= 0.45"
    gates: [pre-train, post-train, pre-deploy]
  serve:
    variants:
      - { name: stable, version: 1.3.0, weight: 80 }
      - { name: candidate, version: 1.4.0, weight: 20 }
  observe:
    drift: { method: psi, threshold: 0.2 }
    lineage: openlineage
"""
)


def spec(**changes):
    """The draft with `changes` applied at dotted paths (None deletes)."""
    doc = copy.deepcopy(DRAFT)
    for dotted, value in changes.items():
        *parents, key = dotted.split(".")
        node = doc
        for part in parents:
            node = node[part]
        if value is None:
            node.pop(key)
        else:
            node[key] = value
    return doc


def test_the_plan_draft_is_a_valid_spec():
    parsed = PipelineSpecV2.model_validate(DRAFT)
    assert parsed.api_version == "godml.io/v2"
    assert parsed.metadata.tags["env"] == "${GODML_ENV:dev}"  # resolved by F2-03
    assert parsed.spec.train.estimator == "xgboost.XGBClassifier"
    assert parsed.spec.govern.gates == ["pre-train", "post-train", "pre-deploy"]


@pytest.mark.parametrize(
    "path",
    [
        "typo",
        "metadata.typo",
        "spec.typo",
        "spec.data.typo",
        "spec.train.typo",
        "spec.govern.typo",
        "spec.serve.typo",
        "spec.observe.typo",
        "spec.observe.drift.typo",
    ],
)
def test_unknown_keys_are_rejected_at_every_level(path):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PipelineSpecV2.model_validate(spec(**{path: 1}))


def test_unknown_key_in_a_variant_is_rejected():
    doc = spec()
    doc["spec"]["serve"]["variants"][0]["typo"] = 1
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PipelineSpecV2.model_validate(doc)


@pytest.mark.parametrize(
    "changes",
    [
        {"apiVersion": "godml.io/v1"},
        {"kind": "Pipeline"},
        {"spec.data.sha256": "abc"},
        {"spec.govern.metrics": {"auc": "0.8"}},
        {"spec.govern.metrics": {"auc": "=> 0.8"}},
        {"spec.govern.gates": ["pre-train", "pre-train"]},
        {"spec.govern.gates": ["after-train"]},
        {"spec.observe.drift": {"method": "kl", "threshold": 0.2}},
        {"spec.observe.drift": {"method": "psi", "threshold": 0}},
        {"spec.observe.lineage": "datahub"},
        {"metadata.name": ""},
        {"spec.data": None},
    ],
)
def test_invalid_values_are_rejected(changes):
    with pytest.raises(ValidationError):
        PipelineSpecV2.model_validate(spec(**changes))


def test_variant_weights_must_add_up_to_100():
    doc = spec()
    doc["spec"]["serve"]["variants"][1]["weight"] = 10
    with pytest.raises(ValidationError, match="add up to 100"):
        PipelineSpecV2.model_validate(doc)


def test_variant_names_must_be_unique():
    doc = spec()
    doc["spec"]["serve"]["variants"][1]["name"] = "stable"
    with pytest.raises(ValidationError, match="unique"):
        PipelineSpecV2.model_validate(doc)


def test_exactly_one_of_train_or_model():
    byom = spec(**{"spec.train": None, "spec.model": {"artifact": "./model.pkl"}})
    assert PipelineSpecV2.model_validate(byom).spec.model.artifact == "./model.pkl"
    both = spec(**{"spec.model": {"artifact": "./model.pkl"}})
    neither = spec(**{"spec.train": None})
    for doc in (both, neither):
        with pytest.raises(ValidationError, match="exactly one"):
            PipelineSpecV2.model_validate(doc)


def test_fixed_sha256_is_accepted_and_normalized():
    digest = "A" * 64
    parsed = PipelineSpecV2.model_validate(spec(**{"spec.data.sha256": digest}))
    assert parsed.spec.data.sha256 == "a" * 64


def test_minimal_spec_uses_defaults():
    minimal = {
        "apiVersion": "godml.io/v2",
        "kind": "ModelPipeline",
        "metadata": {"name": "m", "version": "1"},
        "spec": {
            "data": {"uri": "d.csv", "target": "y"},
            "train": {"estimator": "xgboost"},
        },
    }
    parsed = PipelineSpecV2.model_validate(minimal)
    assert parsed.spec.data.sha256 == "auto"
    assert parsed.spec.govern.policies == []
    assert parsed.spec.serve is None


def test_published_json_schema_is_up_to_date():
    published = json.loads((ROOT / "schemas" / "godml-v2.json").read_text("utf-8"))
    assert published == json_schema(), "run: python -m godml.core.spec"


def test_json_schema_forbids_unknown_keys_everywhere():
    schema = json_schema()
    assert schema["additionalProperties"] is False
    for name, definition in schema["$defs"].items():
        assert definition.get("additionalProperties") is False, name
