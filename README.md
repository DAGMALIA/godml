# 🤖 GODML — Governed, Observable & Declarative Machine Learning  
**Framework de MLOps con Gobernanza, Trazabilidad y Supply Chain Verificada**

[![PyPI - Version](https://img.shields.io/pypi/v/godml?color=blue)](https://pypi.org/project/godml/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Supply Chain Verified](https://img.shields.io/badge/Supply%20Chain-Verified%20by%20Sigstore-2ea44f?style=flat-square&logo=trustpilot&logoColor=white)](https://search.sigstore.dev/?q=DAGMALIA)
[![SLSA Level](https://img.shields.io/badge/SLSA-v1.0.0-blue.svg)](https://slsa.dev/)
[![Build Verified](https://github.com/DAGMALIA/godml_v2/actions/workflows/safety_scan.yml/badge.svg)](https://github.com/DAGMALIA/godml_v2/actions)

---

## 🚀 GODML v1.0.0 — *Stable Governance Release*

La versión 1.0.0 marca un **hito en la madurez del framework**, incorporando trazabilidad completa, publicación verificada en PyPI y una cadena de suministro auditada mediante **Sigstore + SLSA**.

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

```text
🎯 ¿Qué es este proyecto?

Este proyecto fue generado con GODML , un framework que unifica:

Gobernanza : Trazabilidad y metadatos automáticos

Observabilidad : Tracking completo con MLflow

Declarativo : Configuración simple en YAML


- 📦 Novedades en la versión 1.0.0 — Stable Governance Release

- 🧪 Entrenamiento rápido y reproducible desde notebooks con GodmlNotebook

- 💾 Gestión de entornos para modelos (experiments, dev, qa, prod)

- 🧩 Evaluación con validación cruzada (evaluate_with_cv) — compatible con RandomForest, XGBoost y LogisticRegression

- ⚖️ Motor de evaluación dinámica con MetricJudge, que compara métricas y valida umbrales definidos en YAML

- 🧠 Advisor inteligente (advisor_full_report) para análisis automático de desempeño y sugerencias de tuning

- 🪶 Cumplimiento PCI-DSS y detección automática de PII con enmascaramiento seguro

- 🔐 Comando godml security-scan integrado para análisis de vulnerabilidades con Bandit, Safety, Syft y Grype

- 🧾 Cadena de suministro verificada (SBOM + Provenance firmados con Sigstore y SLSA v1)

- 📡 Notebook API ampliada, con funciones como compare_models, dataprep_run_inline, save_artifact, y emit_lineage

- 🔭 Observabilidad mejorada con registro de datasets, métricas y experimentos en MLflow

- 🧰 CLI extendido con nuevos comandos:

  godml init — inicializa proyectos declarativos

  godml run — ejecuta pipelines completos

  godml serve — despliega modelos en FastAPI


- 🧬 Compatibilidad con Supply Chain Secure Build, integrando Bandit, Safety, Cosign y SLSA

- 🧩 Integración con Prometheus & Grafana (experimental) para métricas de modelo y monitoreo en tiempo real

- 🚀 Publicación segura en PyPI con Trusted Publisher (OIDC keyless)
```


```text
📁 Estructura del Proyecto
                
mi-proyecto-ml/
├── godml.yml              # 🎯 Configuración principal
├── data/                  # 📊 Datasets
├── outputs/               # 📈 Predicciones
├── models/                # 🤖 Modelos por entorno
│   ├── production/
│   ├── staging/
│   └── experiments/
├── deploy_service/        # 🚀 Servicios de despliegue
├── Dockerfile             # 🐳 Contenedor Docker
└── README.md              # 📖 Documentación
```

⚙️ Configuración del Pipeline

El archivo godml.yml contiene toda la configuración:

```yaml title="godml.yml (mínimo viable)"
Dataset

dataset:
  uri: ./data/your_dataset.csv  # ← Cambia por tu archivo
  hash: auto                    # Hash automático para trazabilidad

Modelo

model:
  type: xgboost                 # Algoritmo a usar
  hyperparameters:              # Parámetros del modelo
    max_depth: 5
    eta: 0.3
    objective: binary:logistic

Métricas de Calidad

metrics:
- name: auc
  threshold: 0.85              # Umbral mínimo de calidad
- name: accuracy
  threshold: 0.80

Gobernanza

governance:
  owner: your-team@company.com  # ← Cambia por tu email
  tags:
  - project: {project_name}
  - environment: development    # development/staging/production

```
🔧 Modelos Disponibles
Algoritmo	Tipo	Comando
xgboost	Gradient Boosting	Por defecto
random_forest	Ensemble	Cambiar en model.type
lightgbm	Gradient Boosting	Cambiar en model.type

📊 Métricas Soportadas

auc - Area Under Curve

accuracy - Precisión

precision - Precisión por clase

recall - Recall por clase

f1 - F1 Score

🎯 Flujo de Trabajo

```bash

#1. Preparar Datos
#Coloca tu dataset en data/

cp mi_dataset.csv data/your_dataset.csv

#2. Configurar Pipeline
#Edita godml.yml según tus necesidades

vim godml.yml

#3. Entrenar Modelo
#Ejecuta el pipeline completo

godml run -f godml.yml

#4. Revisar Resultados
#Ver experimentos en MLflow

mlflow ui

#Ver predicciones
cat outputs/predictions.csv

```

🧪 Entrenamiento desde Notebooks

```python

from godml.notebook_api import GodmlNotebook

godml = GodmlNotebook()
godml.create_pipeline(
    name="churn_rf",
    model_type="random_forest",
    hyperparameters={"max_depth": 3},
    dataset_path="./data/churn.csv"
)

godml.train()
godml.save_model(model, model_name="churn_rf", environment="experiments")

⚡ Entrenamiento rápido con una línea

from godml.notebook_api import quick_train

quick_train(
    model_type="xgboost",
    hyperparameters={"eta": 0.1, "max_depth": 4},
    dataset_path="./data/churn.csv"
)

🔁 Desde YAML (interactivo)

from godml.notebook_api import train_from_yaml, quick_train_yaml

train_from_yaml("./godml/godml.yml")

quick_train_yaml(
    model_type="random_forest",
    hyperparameters={"max_depth": 4},
    yaml_path="./godml/godml.yml"
)
```

🏛️ Gobernanza y Trazabilidad
GODML automáticamente registra:

✅ Hash del dataset para trazabilidad

✅ Metadatos del modelo (parámetros, métricas)

✅ Información de gobernanza (owner, tags)

✅ Timestamp y versión de cada experimento

✅ Linaje completo del pipeline

🚀 Próximos Pasos
Agregar tus datos: Coloca tu dataset en data/

Personalizar configuración: Edita godml.yml

Entrenar modelo: Ejecuta godml run -f godml.yml

Monitorear: Revisa resultados en MLflow UI

Iterar: Ajusta parámetros y vuelve a entrenar

📚 Recursos Útiles

📦 GODML en PyPI

📖 Documentación oficial (próximamente)

🏛️ Guía de Gobernanza (en construcción)

💬 Soporte / Issues

🐛 Reportar Issues

💬 Discusiones

📧 Contacto

📄 Licencia
Este proyecto está bajo la licencia MIT. Ver LICENSE para más detalles.

Generado con ❤️ por GODML Framework v0.3.0
Governed, Observable & Declarative Machine Learning
---

## 🚀 Cómo Empezar

# Se recomienda crear un entorno virtual

```bash
# 1. Instala el CLI
pip install godml

# 2. Inicializa un proyecto
godml init my-churn-project

# 3. Declara tu pipeline
vim godml.yml

# 4. run
godml run -f godml.yml
```