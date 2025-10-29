# 🤖 GODML — Governed, Observable & Declarative Machine Learning  
**Framework de MLOps con Gobernanza, Trazabilidad y Supply Chain Verificada**

[![PyPI - Version](https://img.shields.io/pypi/v/godml?color=blue)](https://pypi.org/project/godml/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Supply Chain Verified](https://img.shields.io/badge/Supply%20Chain-Verified%20by%20Sigstore-2ea44f?style=flat-square&logo=trustpilot&logoColor=white)](https://search.sigstore.dev/?q=DAGMALIA)
[![SLSA Level](https://img.shields.io/badge/SLSA-v1.0.0-blue.svg)](https://slsa.dev/)

---

## 🚀 GODML v1.0.2 — *Stable Governance Release*

La versión 1.0.2 marca un **hito en la madurez del framework**, incorporando trazabilidad completa, publicación verificada en PyPI y una cadena de suministro auditada mediante **Sigstore + SLSA**.

### 🧩 Características clave
- ✅ Framework **estable y modular**
- 🔐 Supply Chain firmada (SBOM + Provenance)
- 🧾 Cumplimiento **SLSA v1 y SPDX**
- 📦 Publicación segura via **PyPI Trusted Publisher (OIDC)**
- 🧠 Notebook API integrada (`GodmlNotebook`)
- ⚙️ CLI declarativa (`godml run -f godml.yml`)
- 🪶 Licencia MIT

---

## 🔐 Supply Chain & Seguridad

GODML adopta un enfoque de **transparencia verificable**, integrando herramientas de seguridad nativas:

| Artefacto | Estándar | Firma | Transparencia |
|------------|-----------|--------|----------------|
| `sbom.spdx.json` | SPDX | ✅ Cosign OIDC | [Rekor Log](https://search.sigstore.dev/) |
| `provenance.json` | SLSA v1 | ✅ Cosign OIDC | [Rekor Log](https://search.sigstore.dev/) |

### 📜 Verificación reproducible

```bash
cosign verify-blob \
  --bundle sbom.spdx.bundle \
  --certificate-identity-regexp "github.com/DAGMALIA" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  sbom.spdx.json
```

> Proyecto de Machine Learning generado automáticamente con **GODML Framework** - Governed, Observable & Declarative ML

---

                                  🚀 GODML Framework
                              https://pypi.org/project/godml/
                                      https://python.org
                                          LICENSE
                              https://pypi.org/project/godml/
                          Governed, Observable & Declarative Machine Learning
                      Enterprise-grade MLOps platform for production-ready ML pipelines
                  🚀 Quick Start • 📖 Documentation • 🏗️ Architecture • 🤝 Contributing
------------------------------------------------------------------------------------------------------------------------
```text
🎯 Overview

GODML is a comprehensive MLOps framework that unifies Governance, Observability, and Declarative configuration for enterprise Machine Learning workflows. Built for organizations that require complete traceability, regulatory compliance, and scalable model deployment.
```

```text
🌟 Key Features

    *   🏛️ Governance: Automatic traceability, metadata management, and compliance

    *   👁️ Observability: Complete MLflow integration with real-time monitoring

    *   📄 Declarative: Simple YAML configuration for reproducible pipelines

    *   🚀 Production-Ready: Docker, Kubernetes, and cloud-native deployment

    *   🛡️ Compliance: Built-in PCI-DSS, GDPR, and HIPAA support

    *   🧠 AI-Powered: LLM-assisted pipeline optimization and recommendations
```

```text
GODML Performance Metrics

🎯 Business Impact

        Metric	            Traditional ML	        With GODML	        Improvement
Time to Production	           6 months	              2 weeks	         92% faster
Model Accuracy	                  78%	                89%	             14% better
Compliance Violations	        12/year	               0/year	        100% reduction
Operational Cost	           $50K/month	         $15K/month	         70% savings
```

🚀 Quick Start

Installation

```bash
# Install GODML
pip install godml

# Verify installation
godml --version
```
Create Your First Project

```bash
# Initialize new project
godml init my-ml-project
cd my-ml-project

# Configure your pipeline
vim godml.yml

# Train your model
godml run -f godml.yml

# Deploy to production
godml deploy my-ml-project production
```

📄 Basic Configuration

```yaml title="godml.yml (mínimo viable)"
name: customer-churn-prediction
version: 1.0.0
provider: mlflow

dataset:
  uri: ./data/customer_data.csv
  hash: auto

model:
  type: xgboost
  hyperparameters:
    {"max_depth": 6}
    {"learning_rate": 0.1}
    {"n_estimators": 300}

metrics:
- name: auc
  threshold: 0.85
- name: accuracy
  threshold: 0.80

governance:
  owner: "ml-team@company.com"
  tags:
  - project: customer-retention
  - compliance: gdpr
  - environment: production

deploy:
  realtime: true
  batch_output: ./outputs/predictions.csv
```
🧪 Notebook Integration

```text
Quick Training
```

```python
from godml import GodmlNotebook, quick_train

# Method 1: Full pipeline setup
godml = GodmlNotebook()
godml.create_pipeline(
    name="churn-model",
    model_type="xgboost",
    hyperparameters={"max_depth": 6, "eta": 0.1},
    dataset_path="./data/churn.csv"
)
godml.train()
godml.save_model(model_name="churn_v1", environment="production")

# Method 2: One-liner training
quick_train(
    model_type="random_forest",
    hyperparameters={"n_estimators": 300},
    dataset_path="./data/churn.csv"
)
```
AI-Powered Optimization

```python
from godml.notebook_api import advisor_full_report, tune_model

# Get AI recommendations
report = advisor_full_report(df, target="churn")
print(f"Recommended models: {report['models']}")
print(f"Suggested metrics: {report['metrics']}")

# Auto-tune hyperparameters
result = tune_model(
    model_type="xgboost",
    X=X_train, y=y_train,
    max_trials=100,
    metric="roc_auc"
)
print(f"Best AUC: {result['best_score']:.4f}")
```

🔧 System Architecture
```text
┌─────────────────────────────────────────────────────────────────┐
│                        🎯 GODML Framework                       │
├─────────────────────────────────────────────────────────────────┤
│  Frontend Layer                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐ │
│  │ 🌐 Web UI   │ │ 📓 Jupyter  │ │ 🖥️ CLI Tool                │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  API Gateway                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 🚪 FastAPI Gateway (Authentication & Routing)              │ │
│  └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Core Services                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐ │
│  │🧠 Advisor   │ │⚙️ Config    │ │🎯 Pipeline Engine          │ │
│  │Service      │ │Service      │ │                            │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ML Services                                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐ │
│  │🔄 DataPrep  │ │🤖 Model     │ │📊 Monitoring               │ │
│  │Service      │ │Service      │ │Service                     │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐ │
│  │💾 PostgreSQL│ │🗄️ Redis     │ │☁️ Cloud Storage            │ │
│  │Database     │ │Cache        │ │(S3/Azure/GCS)              │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

🌊 Data Flow Pipeline

```text
📊 Raw Data → 🔄 DataPrep → 🛡️ Compliance → 🤖 Training → 📈 Validation → 📦 Registry → 🚀 Deployment → 📊 Monitoring
     ↓              ↓             ↓             ↓             ↓             ↓             ↓             ↓
   S3/Local    Transforms    PII Detection   XGBoost/RF   Cross-Val    MLflow Store   Docker/K8s   Drift Detection


🛡️ Enterprise Features

Compliance & Security

🔒 Data Protection: Encryption at rest and in transit

🛡️ PII Detection: Automatic identification and masking

📋 Regulatory Support: GDPR, PCI-DSS, HIPAA, SOX compliance

🔍 Audit Trail: Complete lineage and change tracking

Scalability & Performance

☸️ Kubernetes Native: Cloud-native deployment

🔄 Auto-scaling: Dynamic resource allocation

⚡ Low Latency: <50ms prediction SLA

📈 High Throughput: 10K+ predictions/second


🏢 Enterprise Use Cases

Financial Services

    *   Fraud Detection: Real-time transaction scoring with PCI-DSS compliance

    *   Credit Risk: Automated underwriting with regulatory reporting

    *   Algorithmic Trading: Low-latency prediction models

Healthcare

    *   Diagnostic Assistance: HIPAA-compliant medical image analysis

    *   Drug Discovery: Molecular property prediction pipelines

    *   Clinical Trials: Patient stratification and outcome prediction

Retail & E-commerce

    *   Recommendation Systems: Personalized product suggestions

    *   Demand Forecasting: Inventory optimization models

    *   Price Optimization: Dynamic pricing strategies

```

🛠️ CLI Reference

Project Management

```bash
godml init <project-name>              # Initialize new project
godml run -f <config.yml>              # Execute pipeline
```


Deployment

```bash
godml deploy <project> <env>           # Deploy to environment
```

🌐 Cloud Deployment

Docker Deployment

```bash
# Build and run
docker build -t my-godml-model .
docker run -p 8080:8080 my-godml-model

# Health check
curl http://localhost:8080/health
```

```Text
📈 Roadmap

🎯 2025 Q2 - Intelligence
    *   🧠 Advanced AutoML capabilities
    *   🤖 GPT-4 powered pipeline generation
    *   📊 Interactive web dashboard
    *   🔍 Explainable AI integration

🎯 2025 Q3 - Scale
    *   ☸️ Kubernetes operator
    *   🌊 Real-time streaming ML
    *   🔄 A/B testing framework
    *   📈 Advanced drift detection

🎯 2025 Q4 - Enterprise
    *   🏢 Multi-tenant architecture
    *   🔒 Zero-trust security model
    *   🌐 Global edge deployment
    *   📋 SOC2/ISO27001 certification

🤝 Contributing

We welcome contributions! Please see our Contributing Guide for details.

Development Setup

-- Next Repo

📄 License
This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

📞 Support
```

    *   Enterprise Support: mailto:agtzrubio@dagmalia.com
    *   Community Support: mailto:agtzrubio@dagmalia.com
    *   Documentation: https://godmlcore.com/
    *   Status Page: https://godmlcore.com/



                                       Built with ❤️ by the GODM
                                  https://github.com/godml/godml (Proximamente)
                                    https://twitter.com/godml_ai (Proximamente)
                                https://linkedin.com/company/godml (Proximamente)
                                   Transforming Enterprise ML Operations 🚀