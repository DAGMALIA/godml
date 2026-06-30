<p align="center">
  <a href="https://pypi.org/project/godml/" target="_blank">
    <img src="https://img.shields.io/pypi/v/godml?style=flat-square&logo=pypi&logoColor=white&color=4f46e5" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/godml/" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/godml?style=flat-square&logo=python&logoColor=white&color=4f46e5" alt="Python versions">
  </a>
  <a href="https://github.com/DAGMALIA/godml/actions/workflows/ci.yml" target="_blank">
    <img src="https://img.shields.io/github/actions/workflow/status/DAGMALIA/godml/ci.yml?branch=main&style=flat-square&logo=githubactions&logoColor=white&label=ci" alt="CI">
  </a>
  <a href="https://codecov.io/gh/DAGMALIA/godml" target="_blank">
    <img src="https://img.shields.io/codecov/c/github/DAGMALIA/godml?style=flat-square&logo=codecov&logoColor=white&color=22c55e" alt="Coverage">
  </a>
  <a href="https://github.com/DAGMALIA/godml/blob/main/LICENSE" target="_blank">
    <img src="https://img.shields.io/badge/license-MIT-7c3aed?style=flat-square" alt="MIT License">
  </a>
  <a href="https://www.godmlcore.com" target="_blank">
    <img src="https://img.shields.io/badge/docs-godmlcore.com-0891b2?style=flat-square" alt="Docs">
  </a>
</p>
<p align="center">
  <a href="https://slsa.dev/" target="_blank">
    <img src="https://img.shields.io/badge/SLSA-level%203-f59e0b?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAxTDMgNXY2YzAgNS41NSAzLjg0IDEwLjc0IDkgMTIgNS4xNi0xLjI2IDktNi40NSA5LTEyVjVsLTktNHoiLz48L3N2Zz4=&logoColor=white" alt="SLSA Level 3">
  </a>
  <a href="https://search.sigstore.dev/?q=DAGMALIA" target="_blank">
    <img src="https://img.shields.io/badge/sigstore-keyless-7c3aed?style=flat-square" alt="Sigstore">
  </a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/DAGMALIA/godml" target="_blank">
    <img src="https://api.securityscorecards.dev/projects/github.com/DAGMALIA/godml/badge" alt="OpenSSF Scorecard">
  </a>
  <a href="https://github.com/DAGMALIA/godml/actions/workflows/safety_scan.yml" target="_blank">
    <img src="https://img.shields.io/github/actions/workflow/status/DAGMALIA/godml/safety_scan.yml?branch=main&style=flat-square&logo=githubactions&logoColor=white&label=supply+chain&color=db2777" alt="Supply Chain">
  </a>
</p>

<h1 align="center">GODML</h1>
<p align="center"><strong>Governed, Observable & Declarative Machine Learning Framework</strong></p>
<p align="center">
  Production-grade MLOps for teams that need traceability, compliance, and a verified supply chain — without the infrastructure overhead.
</p>

---

## Quick start

```bash
pip install godml
godml init my-project
godml run -f godml.yml
```

That's it. No cloud account required for local training.

---

## What is GODML?

GODML is a Python framework that wraps the full ML lifecycle — data prep, training, evaluation, monitoring, and deployment — behind a single declarative YAML config. Every run produces a signed, auditable artifact trail.

```
Raw data → Compliance check → Train → Evaluate → Registry → Deploy → Monitor
               (PII/GDPR)    (XGB/RF/LR)  (cross-val)  (MLflow)  (Docker)  (drift)
```

### Why GODML over plain sklearn + MLflow?

| Problem | Without GODML | With GODML |
|---------|--------------|------------|
| Reproducibility | Manual notebooks | Declarative YAML, locked hashes |
| Compliance | Ad-hoc checks | Built-in PCI-DSS, GDPR, HIPAA |
| Supply chain | No SBOM | SLSA L3 provenance + signed SBOM |
| Audit trail | Scattered logs | Unified lineage per run |
| Multi-model | Custom glue code | Registry + `notebook_api` |

---

## Installation

### Core (no optional deps)

```bash
pip install godml
```

### With extras

```bash
pip install "godml[advisor]"   # LLM-powered recommendations (gpt4all)
pip install "godml[deep]"      # LSTM forecasting (tensorflow + keras)
pip install "godml[aws]"       # SageMaker deployment
pip install "godml[api]"       # REST inference server (fastapi + uvicorn)
pip install "godml[dev]"       # Full dev suite (tests, lint, coverage)
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
  hash: auto

model:
  type: xgboost
  hyperparameters:
    max_depth: 6
    learning_rate: 0.1
    n_estimators: 300

metrics:
  - name: auc
    threshold: 0.85
  - name: accuracy
    threshold: 0.80

governance:
  owner: ml-team@company.com
  tags:
    - compliance: gdpr
    - environment: production

deploy:
  realtime: true
  batch_output: ./outputs/predictions.csv
```

Run it:

```bash
godml run -f godml.yml
```

---

## Notebook API

For interactive work in Jupyter:

```python
from godml import GodmlNotebook

nb = GodmlNotebook()
nb.load_data("./data/churn.csv", target="churn")
nb.train_model("xgboost", {"max_depth": 6, "n_estimators": 300})
nb.evaluate(["auc", "accuracy", "f1"])
nb.save_model("churn_v1")
```

### AI-powered advisor

```python
from godml.notebook_api import advisor_full_report, tune_model

# Get model + metric recommendations for your dataset
report = advisor_full_report(df, target="churn")
print(report["recommended_models"])   # ['xgboost', 'random_forest']
print(report["data_quality"])         # quality score + issues

# Auto-tune with Optuna
result = tune_model(
    model_type="xgboost",
    X=X_train, y=y_train,
    max_trials=50,
    metric="auc",
)
print(f"Best AUC: {result['best_score']:.4f}")
```

### Supported model types

| Key | Algorithm |
|-----|-----------|
| `xgboost` / `xgb` | XGBoost |
| `random_forest` / `rf` | scikit-learn RandomForest |
| `logistic_regression` / `logreg` | scikit-learn LogisticRegression |
| `lstm` | LSTM forecasting *(requires `[deep]`)* |

---

## Compliance

```python
from godml.compliance_service import PciDssCompliance, GdprCompliance

compliance = PciDssCompliance()
clean_df = compliance.apply(df)          # masks PAN, CVV, account numbers

gdpr = GdprCompliance()
report = gdpr.apply(df)                  # anonymizes PII per GDPR rules
```

Built-in compliance modules: `PCI-DSS`, `GDPR`, `HIPAA`, `SOX`.  
Custom rules: subclass `BaseCompliance` and implement `apply(df)`.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    GODML Framework                   │
├────────────────┬─────────────┬───────────────────────┤
│  Interfaces    │  Notebook   │  CLI  │  REST API      │
├────────────────┴─────────────┴───────────────────────┤
│  Core Services                                       │
│  ┌───────────┐ ┌───────────┐ ┌──────────────────────┐│
│  │ Advisor   │ │ Config    │ │ Pipeline Engine      ││
│  └───────────┘ └───────────┘ └──────────────────────┘│
├──────────────────────────────────────────────────────┤
│  ML Services                                         │
│  ┌───────────┐ ┌───────────┐ ┌──────────────────────┐│
│  │ DataPrep  │ │ Model     │ │ Monitoring           ││
│  │ +PII scan │ │ Registry  │ │ +Drift detection     ││
│  └───────────┘ └───────────┘ └──────────────────────┘│
├──────────────────────────────────────────────────────┤
│  Providers:  MLflow │ SageMaker │ Docker │ Local      │
└──────────────────────────────────────────────────────┘
```

---

## Supply chain & security

GODML ships with a **SLSA Level 3** supply chain — every release is built in an isolated GitHub Actions environment with unforgeable provenance.

| Artifact | Standard | Signature | Transparency |
|----------|----------|-----------|--------------|
| `sbom.spdx.json` | SPDX 2.3 | Cosign OIDC (keyless) | [Rekor log](https://search.sigstore.dev/?q=DAGMALIA) |
| `sbom.cyclonedx.json` | CycloneDX 1.6 | SLSA provenance | GitHub Release assets |
| `provenance.intoto.jsonl` | SLSA v1 / in-toto | slsa-github-generator | [Rekor log](https://search.sigstore.dev/?q=DAGMALIA) |

### Verify the SBOM yourself

```bash
# Download from GitHub Releases
cosign verify-blob \
  --bundle sbom.spdx.bundle \
  --certificate-identity-regexp "https://github.com/DAGMALIA/godml/.github/workflows/safety_scan.yml" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  sbom.spdx.json
```

### Verify SLSA provenance

```bash
slsa-verifier verify-artifact dist/godml-*.whl \
  --provenance-path provenance.intoto.jsonl \
  --source-uri github.com/DAGMALIA/godml \
  --source-tag v1.1.0
```

### CI security controls

| Control | Tool | Status |
|---------|------|--------|
| SAST | Bandit | ✅ Blocks on HIGH/CRITICAL |
| Dependency CVEs | pip-audit + Safety | ✅ Weekly + per PR |
| SHA-pinned actions | Dependabot | ✅ Auto-pinned |
| PyPI publish | OIDC Trusted Publisher | ✅ No API tokens |
| Branch protection | GitHub Ruleset | ✅ PR + status checks |
| Tag protection | GitHub Ruleset | ✅ `v*` immutable |
| Score | OpenSSF Scorecard | ✅ Published weekly |

---

## CLI reference

```bash
godml init <project>         # scaffold new project
godml run -f godml.yml       # execute pipeline from config
godml deploy <project> <env> # deploy model to environment
godml --version              # print version
```

---

## Roadmap

### v1.2.0 — Q3 2026
- [ ] Interactive drift dashboard (Streamlit)
- [ ] A/B testing framework
- [ ] Optuna distributed tuning

### v1.3.0 — Q4 2026
- [ ] Kubernetes operator
- [ ] Real-time streaming inference
- [ ] Multi-tenant model registry

### v2.0.0 — 2027
- [ ] Multi-cloud provider abstraction (Vertex AI, Azure ML)
- [ ] Federated learning support
- [ ] SOC2 / ISO27001 documentation kit

---

## Contributing

```bash
git clone https://github.com/DAGMALIA/godml.git
cd godml
pip install -e ".[dev]"
pytest tests/ --cov=godml
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch conventions and PR checklist.

---

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  Built by <a href="https://github.com/DAGMALIA">DAGMALIA</a> · 
  <a href="https://pypi.org/project/godml/">PyPI</a> · 
  <a href="mailto:agtzrubio@dagmalia.com">Support</a>
</p>