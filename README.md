<p align="center">
  <img src="https://img.shields.io/pypi/v/godml?color=0066cc&label=godml&logo=pypi&logoColor=white" alt="PyPI">
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://github.com/DAGMALIA/godml/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI">
  <a href="https://github.com/DAGMALIA/godml/actions/workflows/safety_scan.yml?query=branch%3Amain"><img src="https://github.com/DAGMALIA/godml/actions/workflows/safety_scan.yml/badge.svg?branch=main" alt="Safety + supply chain (blocking)"></a>
  <img src="https://img.shields.io/badge/SLSA-Level%203-green?logo=slsa&logoColor=white" alt="SLSA L3">
  <img src="https://api.securityscorecards.dev/projects/github.com/DAGMALIA/godml/badge" alt="OpenSSF Scorecard">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT">
</p>

<h1 align="center">GODML</h1>
<p align="center"><strong>Governed, Observable & Declarative Machine Learning Framework</strong></p>
<p align="center">
  Declarative ML pipelines with fail-closed PCI-DSS compliance, MLflow tracking and a verified release supply chain.
</p>

---

## Quick start

```bash
pip install godml
godml init my-project
cd my-project
# 1. Put your CSV at data/your_dataset.csv
# 2. In godml.yml, set dataset.target to the column you want to predict
# 3. The generated config enables PCI-DSS compliance, which needs a secret key:
export GODML_PII_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
godml run -f godml.yml
```

No cloud account is required for local training (MLflow runs locally).

---

## What is GODML?

GODML drives the ML lifecycle — data prep, compliance, training, evaluation,
registration and serving — from one declarative YAML file.

```
Data → PCI-DSS compliance → Train → Evaluate → MLflow registry → Serve → Monitor
       (mask/hash/drop PII)  (XGB/RF/LR)  (thresholds)          (FastAPI) (Prometheus, PSI drift)
```

Governance is **fail-closed**: if compliance is requested and cannot be
applied, a pinned dataset hash does not match, or a governance check fails,
the run stops instead of continuing with unprocessed data.

| Problem | Without GODML | With GODML |
|---------|--------------|------------|
| Reproducibility | Manual notebooks | Declarative YAML, verified dataset hash |
| Compliance | Ad-hoc checks | Built-in PCI-DSS (mask / HMAC hash / drop) |
| Supply chain | No SBOM | SLSA L3 provenance + SBOM on every release |
| Audit trail | Scattered logs | MLflow run with dataset hash and schema |

---

## Installation

```bash
pip install godml                      # core: CLI, YAML, training with MLflow
pip install "godml[api]"               # REST inference server (fastapi + uvicorn)
pip install "godml[observability]"     # Prometheus metrics for the server
pip install "godml[aws]"               # SageMaker executor (boto3 + sagemaker)
pip install "godml[data]"              # Parquet support for dataprep (pyarrow)
pip install "godml[deep]"              # LSTM forecasting (tensorflow + keras)
pip install "godml[advisor]"           # LLM advisor (gpt4all, local model)
pip install "godml[all]"               # every runtime extra above
```

---

## Configuration

A minimal `godml.yml`:

```yaml
name: customer-churn
version: 1.0.0
provider: mlflow

dataset:
  uri: ./data/churn.csv
  target: churn
  hash: auto            # or the SHA-256 from `godml calc-hash`; verified on run

model:
  type: xgboost
  hyperparameters:
    max_depth: 6
    eta: 0.1
    n_estimators: 300

metrics:
  - name: auc
    threshold: 0.85
  - name: accuracy
    threshold: 0.80

governance:
  owner: ml-team@company.com
  compliance: pci-dss   # optional; requires GODML_PII_KEY (see Compliance)
  policy: mask_sensitive
  tags:
    - environment: production

deploy:
  realtime: false
  batch_output: ./outputs/predictions.csv
```

`${VAR}` and `${VAR:default}` are resolved from the environment anywhere in
the file. For loss metrics (`mse`, `rmse`, `mae`, `log_loss`) the threshold
is an upper bound.

```bash
godml run -f godml.yml
```

---

## Notebook API

```python
from godml.notebook_api import GodmlNotebook

nb = GodmlNotebook()
nb.create_pipeline(
    name="churn_xgb",
    model_type="xgboost",
    hyperparameters={"max_depth": 6, "n_estimators": 300},
    dataset_path="./data/churn.csv",
    target="churn",
)
nb.train()
nb.save_model(model_name="churn_xgb", environment="experiments")
```

Quick one-liner:

```python
from godml.notebook_api import quick_train

quick_train(
    model_type="random_forest",
    hyperparameters={"max_depth": 5},
    dataset_path="./data/churn.csv",
    target="churn",
)
```

### Hyperparameter search

```python
import pandas as pd
from godml.notebook_api import tune_model

df = pd.read_csv("./data/churn.csv")
# tune_model expects numeric features: encode or drop text columns first
X = df.drop(columns=["churn"]).select_dtypes("number")
y = df["churn"]

result = tune_model(model_type="xgboost", X=X, y=y, metric="roc_auc", max_trials=20)
print(result["best_score"], result["best_params"])
```

Randomized search with cross-validation; pass `use_optuna=True` to use Optuna
if it is installed (`pip install optuna`, not included in any extra).

### Advisor (requires `godml[advisor]`)

```python
from godml.notebook_api import advisor_full_report

advisor_full_report(df, target="churn")   # prints task type, suggested models,
                                          # hyperparameter space and data quality
```

### Supported model types

| `model.type` | Algorithm |
|--------------|-----------|
| `xgboost` | XGBoost |
| `random_forest` | scikit-learn RandomForest |
| `logistic_regression` | scikit-learn LogisticRegression |
| `linear_regression` | scikit-learn LinearRegression (regression) |
| `lstm_forecast` | LSTM forecasting *(requires `[deep]`)* |

---

## Compliance

PCI-DSS is the built-in compliance standard. It detects PII by column name
(whole tokens such as `email`, `card_number`, `zip_code`, `lat`) and by
content (card numbers, emails, SSN, phones, IBAN, …), and applies a policy:

| `governance.policy` | Effect |
|---------------------|--------|
| `mask_sensitive` (default) | Masks values (e.g. `us**@example.com`) |
| `hash_sensitive` | HMAC-SHA256 keyed by `GODML_PII_KEY` |
| `drop_sensitive` | Removes the columns |

`GODML_PII_KEY` is required whenever compliance is enabled, with any policy
and in any environment; the run stops without it. Generate it with
`python -c "import secrets; print(secrets.token_hex(32))"`, keep it secret and
use the same key for training and serving. For throwaway local tests only,
`GODML_ALLOW_INSECURE_PII_KEY=1` uses a public dev key (refused with
`GODML_ENV=prod`).

The dataset target is never treated as PII. Any other `governance.compliance`
value stops the run: no other standard is implemented.

```python
from godml.compliance_service.pci_dss import PciDssCompliance

clean_df = PciDssCompliance(policy="drop_sensitive").apply(df)
```

Custom standards: subclass `godml.compliance_service.base_compliance.BaseCompliance`
and implement `apply(df)`.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    GODML Framework                   │
├──────────────────────────────────────────────────────┤
│  Interfaces:  CLI  │  Notebook API  │  REST server   │
├──────────────────────────────────────────────────────┤
│  Config (YAML + ${VAR})  │  Pipeline engine          │
├──────────────────────────────────────────────────────┤
│  DataPrep │ PCI-DSS compliance │ Models │ Monitoring │
│           │ (fail-closed)      │        │ (PSI drift)│
├──────────────────────────────────────────────────────┤
│  Executors:  MLflow (local)  │  SageMaker            │
└──────────────────────────────────────────────────────┘
```

---

## Supply chain & security

Every release is built in GitHub Actions with SLSA Level 3 provenance and
published to PyPI with Trusted Publishing (OIDC). Details and current
enforcement are in [SECURITY.md](SECURITY.md).

| Artifact | Format | Signature | Where |
|----------|--------|-----------|-------|
| Wheel + sdist | `.whl`, `.tar.gz` | Covered by SLSA provenance | GitHub Release, PyPI |
| `multiple.intoto.jsonl` | SLSA v1 / in-toto | slsa-github-generator (Sigstore) | GitHub Release |
| `sbom.cyclonedx.json` | CycloneDX | not signed | GitHub Release |
| `sbom.spdx.json` | SPDX | Cosign keyless (Rekor) | Workflow artifact `supplychain-artifacts` |

### Verify SLSA provenance

```bash
# From the GitHub Release: the wheel and multiple.intoto.jsonl
slsa-verifier verify-artifact godml-<version>-py3-none-any.whl \
  --provenance-path multiple.intoto.jsonl \
  --source-uri github.com/DAGMALIA/godml \
  --source-tag v<version>
```

### Verify the signed SPDX SBOM

```bash
# From the `supplychain-artifacts` artifact of the release workflow run
cosign verify-blob \
  --bundle sbom.spdx.bundle \
  --certificate-identity-regexp "https://github.com/DAGMALIA/godml/.github/workflows/safety_scan.yml" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  sbom.spdx.json
```

### CI security controls

| Control | Tool | Status |
|---------|------|--------|
| SAST | Bandit | Blocks on HIGH |
| Fail-closed lint | ruff (`S110`, `BLE001`) + mypy | Blocks new violations |
| Dependency CVEs | pip-audit + Safety (reviewed ignores) | Blocks, every push and PR |
| Licenses | pip-licenses | Blocks strong copyleft |
| Actions | Pinned by commit SHA, updated by Dependabot | Enforced |
| PyPI publish | OIDC Trusted Publisher | No API tokens |
| Branch / tag protection | GitHub rulesets | `main` and release tags |
| Score | OpenSSF Scorecard | Weekly |

---

## CLI reference

```bash
godml init <project>              # scaffold a project (godml.yml, data/, Dockerfile)
godml run -f godml.yml            # run the pipeline
godml calc-hash <file> [-u godml.yml]  # SHA-256 of a dataset, optionally pinned in the YAML
godml serve [--environment dev]   # serve the model locally (needs [api])
godml deploy <project> <env>      # build and run the Docker image for an environment
godml dataprep --help             # data preparation recipes
godml --version                   # installed version
```

---

## Roadmap

GoDML 2.0 is in progress: installation per pillar (Train, Govern, Serve,
Observe, Tools), a v2 YAML spec with a migration path from 1.x, a single
bundle-based serving runtime and conda-forge packages. 1.x keeps working;
breaking changes come with a migration guide.

---

## Contributing

```bash
git clone https://github.com/DAGMALIA/godml.git
cd godml
pip install -e ".[dev,test-serve,test-observe,test-aws]"
pipx install pre-commit && pre-commit install
pytest tests/ --cov=godml
```

---

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  Built by <a href="https://github.com/DAGMALIA">DAGMALIA</a> ·
  <a href="https://pypi.org/project/godml/">PyPI</a> ·
  <a href="mailto:agtzrubio@dagmalia.com">Support</a>
</p>
