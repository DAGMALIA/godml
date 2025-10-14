Proyecto GODML - Machine Learning con Gobernanza**

[![GODML](https://img.shields.io/badge/Powered%20by-GODML-blue.svg)](https://pypi.org/project/godml/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Supply Chain Verified](https://img.shields.io/badge/Supply%20Chain-Verified%20by%20Sigstore-2ea44f?style=for-the-badge&logo=trustpilot&logoColor=white)](https://search.sigstore.dev/?logIndex=605629063)

GODML adopta un enfoque de **cadena de suministro verificada**, con artefactos firmados de manera *keyless* mediante **Sigstore Cosign** y verificación automatizada en CI/CD.

**Cumplimientos:**
- 📜 SBOM firmado (SPDX)
- 🧾 Provenance conforme a [SLSA v1](https://slsa.dev/)
- 🔑 Certificados efímeros OIDC (GitHub Actions)
- 🪶 Auditoría pública en [Rekor Transparency Log](https://search.sigstore.dev/?logIndex=605629063)

**Archivos generados:**

sbom.spdx.json
sbom.spdx.sig
sbom.spdx.crt
sbom.spdx.bundle
provenance.json
provenance.sig
provenance.crt
provenance.bundle


> 🔍 *Verificación reproducible:*
> ```bash
> cosign verify-blob \
>   --bundle sbom.spdx.bundle \
>   --certificate-identity-regexp "github.com/DAGMALIA" \
>   --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
>   sbom.spdx.json
> ```

---

### 🧠 GODML Supply Chain Summary
- ✅ SBOM y Provenance firmados y verificados
- ✅ Transparencia auditada vía Rekor
- ✅ Sin llaves locales (OIDC Keyless)
- ✅ Compatible con GitHub Advanced Security

---

**Ver registro público:**  
[🔗 Rekor entry #605629063 (SBOM)](https://search.sigstore.dev/?logIndex=605629063)  
[🔗 Rekor entry #605629073 (Provenance)](https://search.sigstore.dev/?logIndex=605629073)


> Proyecto de Machine Learning generado automáticamente con **GODML Framework** - Governed, Observable & Declarative ML

---

🎯 ¿Qué es este proyecto?
Este proyecto fue generado con GODML , un framework que unifica:

Gobernanza : Trazabilidad y metadatos automáticos

Observabilidad : Tracking completo con MLflow

Declarativo : Configuración simple en YAML


📦 Novedades en la versión 0.3.0

- 🧪 Entrenamiento rápido desde notebooks con `GodmlNotebook`
- 💾 Guardado y carga de modelos por entorno (`experiments`, `production`, etc.)
- ⚡ Nuevas funciones `quick_train`, `train_from_yaml`, `quick_train_yaml` para acelerar iteraciones
- 📄 Mejor integración con YAML, sin perder reproducibilidad

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