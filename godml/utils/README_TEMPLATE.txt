# {project_name}
**Proyecto GODML - Machine Learning con Gobernanza**

[![GODML](https://img.shields.io/badge/Powered%20by-GODML-blue.svg)](https://pypi.org/project/godml/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Proyecto generado automáticamente con **GODML Framework** - Governed, Observable & Declarative ML

---

## 🧠 Arquitectura GODML

- **Core Service**: ejecución de modelos
- **Config Service**: validación de YAML y gobernanza
- **Model Service**: entrenamiento, evaluación, registro
- **Monitoring Service**: métricas, trazabilidad, cumplimiento

```
📂 godml/
├── core_service/
├── config_service/
├── model_service/
├── monitoring_service/
├── compliance_service/
```

---

## 📁 Estructura del Proyecto

```
{project_name}/
├── godml.yml              # 🎯 Configuración principal del pipeline
├── data/                  # 📊 Datasets
│   └── your_dataset.csv
├── outputs/               # 📈 Predicciones y resultados
│   └── predictions.csv
├── models/                # 🤖 Modelos entrenados
│   ├── production/
│   ├── staging/
│   └── experiments/
├── mlruns/                # 📋 Experimentos MLflow (auto-generado)
├── requirements.txt       # 📦 Dependencias
└── README.md              # 📖 Documentación
```

---

## ⚙️ YAML de Configuración (`godml.yml`)

```yaml
dataset:
  uri: ./data/your_dataset.csv
  hash: auto

model:
  type: xgboost
  hyperparameters:
    max_depth: 5
    eta: 0.3
    objective: binary:logistic

metrics:
  - name: auc
    threshold: 0.85
  - name: accuracy
    threshold: 0.80

governance:
  owner: your-team@company.com
  tags:
    - project: {project_name}
    - environment: development

deploy:
  realtime: false
  batch_output: ./outputs/predictions.csv
```

---

## 🚀 Flujo de Trabajo

1. **Preparar Datos**  
   `cp mi_dataset.csv data/your_dataset.csv`

2. **Configurar Pipeline**  
   `vim godml.yml`

3. **Entrenar Modelo**  
   `godml run -f godml.yml`

4. **Visualizar Experimentos**  
   `mlflow ui`

---

## 🧪 Entrenamiento desde Notebooks

```python
from godml.notebook_api import GodmlNotebook
godml = GodmlNotebook()
godml.create_pipeline(
    name="churn_rf",
    model_type="random_forest",
    hyperparameters={{"max_depth": 3}},
    dataset_path="./data/churn.csv"
)
godml.train()
godml.save_model("churn_rf", environment="experiments")
```

## ⚡ Entrenamiento rápido

```python
from godml.notebook_api import quick_train

quick_train(
    model_type="xgboost",
    hyperparameters={{"eta": 0.1, "max_depth": 4}},
    dataset_path="./data/churn.csv"
)
```

## 🔁 Desde YAML

```python
from godml.notebook_api import train_from_yaml
train_from_yaml("godml.yml")
```

---

## 🧭 Comandos CLI Disponibles

- `godml init <nombre>`: inicializa proyecto
- `godml run -f godml.yml`: ejecuta pipeline
- `godml hash <path>`: calcula hash de un archivo
- `godml version`: muestra versión instalada

---

## 📊 Métricas Soportadas

- `auc`, `accuracy`, `precision`, `recall`, `f1`

---

## ✅ Cumplimiento y Gobernanza

- Hash de dataset automático
- Metadatos del modelo y métricas
- Soporte para normativas (PCI-DSS, etc.)
- Trazabilidad de experimentos con MLflow

---

# 🧠 GODML Deployment API — Endpoints Documentation

**Servicio:** `deploy_service/server.py`  
**Entorno:** `GODML_ENV = dev | qa | prod`  
**Base URL (local):** `http://127.0.0.1:8000`

---

## 📋 Overview

Esta API expone un microservicio de inferencia para modelos entrenados con **GODML**.  
Está construida con **FastAPI**, lo que permite compatibilidad nativa con OpenAPI (Swagger UI).

El servicio se adapta según el entorno:
| Entorno | Características |
|:--|:--|
| **dev** | Logs detallados, CORS activo, endpoint `/debug/config` habilitado |
| **qa** | Similar a dev, sin autoreload |
| **prod** | Logs JSON minimalistas, CORS desactivado, `/debug/config` deshabilitado |

---

## ⚡ Endpoints principales

### 1️⃣ `/predict`
**Método:** `POST`  
**Descripción:** Ejecuta una predicción con el modelo cargado.  
**Headers:**  
`Content-Type: application/json`  
---

### 2️⃣ `/health`
**Método:** `GET`  
**Descripción:** Verifica la salud general del servicio.  
Usado para *health checks* de Docker, ECS o SageMaker.

---

### 3️⃣ `/metadata`
**Método:** `GET`  
**Descripción:** Devuelve metadatos del modelo actual.

---

### 4️⃣ `/version`
**Método:** `GET`  
**Descripción:** Devuelve las versiones del servicio y del framework GODML.


---

## 🧩 Endpoints adicionales

### `/docs`
**Método:** `GET`  
**Descripción:** Interfaz Swagger UI autogenerada para pruebas manuales.  
**Ruta:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### `/openapi.json`
**Método:** `GET`  
**Descripción:** Esquema OpenAPI para integraciones y generación de SDKs.  
**Ruta:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

### `/debug/config` *(solo en dev o qa)*
**Método:** `GET`  
**Descripción:** Endpoint de diagnóstico.  
**Solo disponible cuando** `GODML_ENV=dev` o `qa`.


---

## 🩺 Healthcheck Docker/ECS

Puedes agregar esta validación en tu `Dockerfile` o ECS Task Definition:
```dockerfile
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
```

---

## 🧠 Notas técnicas

| Campo | Descripción |
|:--|:--|
| `GODML_ENV` | Controla el modo de ejecución (`dev`, `qa`, `prod`) |
| `MODE` | Se usa internamente por el entrypoint de la imagen base |
| `PORT` | Puerto expuesto por FastAPI (por defecto 8000) |
| `models/dev/model.pkl` | Ruta del modelo cargado por el servicio |
| `godml.yml` | Archivo de configuración del pipeline GODML |

---

## 🧱 Ejemplo de ejecución local

```bash
docker run -p 8000:8000   -e GODML_ENV=dev   -v $(pwd):/app   godml:dev
```

Y luego prueba los endpoints:
```
http://127.0.0.1:8000/health
http://127.0.0.1:8000/predict
http://127.0.0.1:8000/docs
```

---

## 🧩 Recursos relacionados
- [Repositorio GODML en GitHub](https://github.com/dagmalia/godml)
- [Documentación oficial FastAPI](https://fastapi.tiangolo.com/)
- [Dagmalia AI Platform](https://dagmalia.com)

---

## 📚 Recursos

- [GODML en PyPI](https://pypi.org/project/godml/)
- Documentación oficial (https://godmlcore.com/)
- Guía de gobernanza (en construcción)

--

© 2025 **godmlcore** — Arquitectura GODML
Creado por [Arturo Gutiérrez Rubio R.](mailto:agtzrubio@dagmalia.com)

                      Generado con ❤️ por **GODML Framework v1.0.0**