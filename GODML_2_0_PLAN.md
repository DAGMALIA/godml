# GoDML 2.0 — Plan maestro

> **GoDML** — Governed · Observable · Declarative Machine Learning
> Del YAML a producción: **entrenar → gobernar → servir → observar**, con herramientas de productividad alrededor.

Este documento es la fuente de verdad del proyecto 2.0. Claude Code lo lee al iniciar cada sesión y **actualiza los estados** al terminar cada tarea (ver `CLAUDE.md`).

**Leyenda de estado:** ⬜ pendiente · 🟨 en progreso · ✅ hecho · ⛔ bloqueado · ⏭️ descartado

---

## 0. Tablero de estado

| Fase | Nombre | Versión objetivo | Estado |
|---|---|---|---|
| F0 | Fundaciones del repo | 1.4.0 | ✅ |
| F1 | Hotfixes críticos 1.x (protege usuarios actuales) | 1.4.0 | 🟨 |
| F2 | Arquitectura 2.0: core, spec v2, plugins | 2.0.0a1 | ⬜ |
| F3 | Pilar **Govern** | 2.0.0a1 | ⬜ |
| F4 | Pilar **Train** | 2.0.0a2 | ⬜ |
| F5 | Pilar **Serve** | 2.0.0b1 | ⬜ |
| F6 | Pilar **Observe** | 2.0.0b1 | ⬜ |
| F7 | Pilar **Tools** | 2.0.0b2 | ⬜ |
| F8 | Empaquetado: PyPI por pilar + conda-forge | 2.0.0rc1 | ⬜ |
| F9 | Docs, ejemplos, migración y lanzamiento | 2.0.0 | ⬜ |

**Fase activa:** F1

---

## 1. Visión de producto

### Los 5 pilares

| Pilar | Qué resuelve | Comandos principales |
|---|---|---|
| **Train** | Entrenar modelos desde YAML: catálogo propio, cualquier estimador sklearn-compatible, o "bring your own model" (.pkl ya entrenado) | `godml run`, `godml train` |
| **Govern** | Contratos y políticas *fail-closed*: owner, hash de datos verificado, PII/PCI-DSS, umbrales de métricas, gates pre/post/deploy, repo central multi-modelo | `godml validate`, `godml govern check` |
| **Serve** | Un runtime único que consume un *bundle* (modelo + pre/post + firma + baseline + manifiesto), con A/B y canary declarativos | `godml serve`, `godml deploy`, `godml bundle` |
| **Observe** | Métricas Prometheus, drift PSI, dashboards Grafana, linaje OpenLineage, comparación entre variantes A/B | `godml observe`, `godml drift` |
| **Tools** | Productividad: scaffolding, notebook API, recetas de preprocesamiento, migración 1.x→2.0, advisor LLM y RAG | `godml init`, `godml migrate`, `godml advisor` |

### Patrón de referencia: repo central (probado a 500+ modelos)

```
models-repo/
├── godml.defaults.yaml          # defaults heredables (owner, políticas, observabilidad)
├── teams/
│   └── revenue.defaults.yaml    # defaults por equipo
└── models/
    ├── churn-predictor/
    │   ├── godml.yaml           # contrato del modelo
    │   ├── model.pkl            # opcional: bring-your-own-model
    │   ├── preprocess.py        # hook de preprocesamiento
    │   └── postprocess.py       # hook de postprocesamiento
    └── fare-forecast/
        └── godml.yaml
```

`godml validate models/` valida el repo completo en CI; `godml run models/churn-predictor` opera un modelo individual.

### Spec v2 (borrador; se formaliza en F2)

```yaml
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
    sha256: auto                      # 'auto' en dev; hash fijo obligatorio en prod
    target: churned
  train:                              # pilar Train (omitir si es bring-your-own-model)
    estimator: xgboost.XGBClassifier  # o alias del catálogo: "xgboost"
    params: { max_depth: 5, n_estimators: 200 }
    preprocess: { recipe: ./recipes/churn.yaml }
  model:                              # alternativa: bring-your-own-model
    artifact: ./model.pkl
    preprocess: ./preprocess.py
    postprocess: ./postprocess.py
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
```

---

## 2. Arquitectura objetivo

### 2.1 Layout del paquete

```
godml/
├── core/        # spec v2, loader único, resolver ${VAR}, errores, logging, registro de plugins
├── govern/      # políticas, gates, PII, hashing (HMAC), verificación de datos, validación de repo
├── train/       # executors (local, mlflow, sagemaker), catálogo, estimadores por import path, métricas
├── serve/       # bundle, runtime FastAPI único, enrutamiento A/B, Docker
├── observe/     # Prometheus, drift PSI, baseline, OpenLineage, dashboards
├── tools/       # init, notebook API, recetas, migrate, advisor, rag
└── cli/         # typer; cada subcomando importa su pilar de forma perezosa
```

**Reglas de arquitectura**

- `core` no depende de ningún pilar. Cada pilar depende solo de `core` (y opcionalmente de `govern`).
- Importar `godml` no tiene efectos colaterales: no crea carpetas, no configura logging raíz, no filtra warnings.
- Si falta el extra de un pilar, el error es claro: `GoDMLMissingExtra: instala 'godml[serve]' para usar este comando`.
- Executors, políticas y estimadores se registran vía *entry points* (`godml.executors`, `godml.policies`, `godml.estimators`) para permitir plugins de terceros.
- Toda falla de gobernanza es **fail-closed**. Queda prohibido `except Exception: pass` (regla de lint).

### 2.2 Instalación por pilar (PyPI)

```bash
pip install godml                    # core: spec, validate, CLI
pip install "godml[govern]"          # gobernanza: PII, hashing, gates
pip install "godml[train]"           # entrenamiento: sklearn, xgboost, mlflow
pip install "godml[serve]"           # serving: fastapi, uvicorn
pip install "godml[observe]"         # observabilidad: prometheus, openlineage
pip install "godml[tools]"           # init, notebook, recetas, migrate

# Sub-extras pesados (opt-in explícito)
pip install "godml[train-dl]"        # tensorflow (LSTM)
pip install "godml[train-aws]"       # sagemaker, boto3
pip install "godml[tools-ai]"        # advisor LLM + RAG

pip install "godml[all]"             # todo, equivalente a 1.x
```

| Extra | Dependencias propuestas (rangos a fijar en F8) |
|---|---|
| *core* | pydantic>=2, pyyaml, typer, rich |
| `govern` | pandas, pyarrow |
| `train` | `govern` + scikit-learn, xgboost, mlflow |
| `train-dl` | `train` + tensorflow |
| `train-aws` | `train` + sagemaker, boto3 |
| `serve` | fastapi, uvicorn, joblib |
| `observe` | prometheus-client, openlineage-python |
| `tools` | jinja2 (scaffolding), nbformat (si aplica) |
| `tools-ai` | `tools` + cliente LLM / embeddings (definir en F7) |
| `all` | todos los anteriores |

### 2.3 Instalación por pilar (conda-forge)

conda no soporta extras, así que se usa una **receta multi-output** (mismo patrón que `dask`/`dask-core`):

```bash
conda install -c conda-forge godml-core
conda install -c conda-forge godml-govern
conda install -c conda-forge godml-train
conda install -c conda-forge godml-serve
conda install -c conda-forge godml-observe
conda install -c conda-forge godml-tools
conda install -c conda-forge godml           # metapaquete: todo
```

Requisito: el paquete debe ser `noarch: python` (puro Python). **Implica retirar la extensión Cython** o dejarla solo como acelerador opcional fuera del paquete conda.

---

## 3. Decisiones

| ID | Decisión | Estado |
|---|---|---|
| D1 | Licencia única del proyecto: **MIT** (lo que declaran pyproject, README y headers; se reemplaza el texto Apache-2.0 del archivo LICENSE) | ✅ decidido 2026-10-24 |
| D2 | Versiones de Python soportadas: **3.11+** (3.10 llega a fin de vida en octubre 2026; se mantiene el piso actual). 1.3.1 conserva `>=3.11,<3.14`; 2.0 agrega 3.14 a la matriz y quita el techo si los tests pasan | ✅ revisado 2026-10-24 |
| D3 | Código, docstrings y errores en **inglés**; docs en **EN + ES** | ✅ decidido 2026-10-24 |
| D4 | **Retirar Cython** del core (requisito para conda noarch) | ✅ decidido 2026-10-24 |
| D5 | Rama `1.x` solo con fixes de seguridad durante **6 meses** tras 2.0.0 | ✅ decidido 2026-10-24 |
| D6 | Fuente única de versión: `importlib.metadata.version("godml")` | ✅ decidido 2026-10-24 |
| D7 | Build conda con **rattler-build** (`recipe.yaml` v1) | ✅ decidido 2026-10-24 |
| D8 | Titularidad: el mantenedor revisó su contrato y no hay cláusula que reclame GoDML. El correo corporativo en commits se debe a la config de git en su PC personal. No se reescribe historial; se unifica con .mailmap hacia la identidad de Dagmalia (F0-14) | ✅ resuelto 2026-10-24 |
| D9 | F0-04: el formateo masivo (`ruff format`) va en un **commit aislado primero**, registrado en `.git-blame-ignore-revs` | ✅ 2026-10-24 |
| D10 | Safety se mantiene como escáner bloqueante junto a pip-audit, con API key (SAFETY_API_KEY sigue vigente). Su badge en el README solo refleja un scan bloqueante y con ignores revisados | ✅ 2026-10-25 (revierte la versión anterior de D10) |
| D11 | La versión de hotfixes se publica como 1.4.0 (no 1.3.1) porque fail-closed cambia comportamiento visible (compliance no soportado ahora aborta) | ✅ 2026-10-24 |

---

## 4. Fases y tareas

Formato: **ID** · estado · descripción → *criterio de aceptación*

### F0 — Fundaciones del repo (1.4.0)

- **F0-01** ✅ Licencia MIT (D1): reemplazar el texto de `LICENSE` por MIT estándar con línea de copyright del autor; usar `license = "MIT"` (SPDX) en `pyproject.toml`; verificar classifiers, headers y README; revisar en el historial si hubo contribuciones externas (si las hay, pedir consentimiento para el cambio de texto) y nota en CHANGELOG aclarando que el proyecto siempre se distribuyó como MIT → *`MIT` es el único identificador de licencia en todo el repo*
- **F0-02** ✅ Fuente única de versión (D6); eliminar versiones hardcodeadas en banners, plantillas, `service_version` y SECURITY.md → *`grep` de versiones literales sin resultados fuera de pyproject*
- **F0-03** ✅ Eliminar `godml.egg-info/` del repo y verificar `.gitignore`
- **F0-04** ✅ Tooling: ruff (lint + format), mypy (modo gradual), pre-commit; regla que prohíba `except Exception: pass` (ruff `S110`, `BLE001`) → *CI falla con violaciones*
- **F0-05** ✅ CI que realmente bloquea: quitar `|| true` de bandit y pip-audit; matriz de Python según D2
- **F0-06** ✅ Eliminar workflow suelto `godml/deploy_service/.github/workflows/docker-ci.yml` (acciones sin pinear)
- **F0-07** ✅ Alinear SECURITY.md con la realidad: IDs de Safety ignorados, lockfile, SBOM, fecha de revisión
- **F0-08** ✅ Correr suite actual y registrar línea base (tests pasando, cobertura) en el log de estado
- **F0-09** ✅ **(hacer primero)** Integrar a `main` la rama `chore/bump-version-1.2.2` (fix de `skops_trusted_types` para XGBoost + bump); verificar la última versión publicada en PyPI para numerar correctamente 1.3.1 → *main contiene ambos commits, instalación editable reporta la versión correcta*
- **F0-10** ✅ Cobertura real: eliminar la lista `omit` de `[tool.coverage.run]` (salvo tests y código generado); `fail_under` se fija a la cobertura real actual (~41 %) y sube por fase → *el reporte de CI coincide con la cobertura sin exclusiones*
- **F0-11** ✅ Quitar `-p no:warnings` de `addopts`; usar `filterwarnings` explícitos y tratar como error los `DeprecationWarning` emitidos por `godml` → *los warnings de terceros siguen visibles; los propios fallan el test*
- **F0-12** ✅ `LICENSE_REPORT.md` generado automáticamente (pip-licenses) en CI en lugar de mantenerse a mano
- **F0-13** ✅ Extras de desarrollo mínimos: reemplazar moto[all] por los servicios que usan los tests (p. ej. moto[s3,sagemaker]); separar `dev` en `dev` + `test-<pilar>`; el job `licenses` deja de instalar .[all] (sin tensorflow) y agrega --fail-on para copyleft fuerte → *ningún test se salta por dependencia faltante y `dev` no arrastra fastapi/boto3 de forma oculta*
- **F0-14** ✅ `.mailmap` que unifica las identidades del mantenedor en `Arturo Gutiérrez Rubio Rojas <agtzrubio@dagmalia.com>`, sin reescribir historial → *`git shortlog -sne` muestra una sola identidad humana*
- **F0-15** ⏭️ Retirar Safety (D10): eliminar el workflow/job y sus 15 ignores; actualizar SECURITY.md — *reemplazada por F0-16 al revertirse D10*
- **F0-16** ✅ Safety honesto: (1) restaurar el job de Safety (manteniendo `safety_scan.yml` por la identidad Cosign); (2) sin `continue-on-error`: Safety bloquea CI; (3) revalidar los 15 IDs ignorados contra las versiones que CI resuelve hoy (mlflow 3.17.x, etc.): eliminar los que ya no aplican, y los que se queden llevan motivo, paquete afectado y fecha de revisión; (4) SECURITY.md lista exactamente esos ignores y su política de revisión (cada release y como máximo cada 90 días); (5) badge de Safety en el README apuntando al resultado real del workflow

### F1 — Hotfixes críticos 1.x (1.4.0)

Cada fix lleva primero un test que reproduce el bug.

- **F1-01** ✅ Compliance fail-closed: `ComplianceEngine.apply`, `run_pipeline_preprocessing` y `MLflowExecutor.run` dejan de devolver el df original ante error → *test: excepción en compliance aborta el pipeline*
- **F1-02** ✅ No subir el dataset crudo a MLflow; registrar solo hash y esquema (o el dataset ya cumplido si se pide explícitamente) → *test: el artefacto de MLflow no contiene columnas PII*
- **F1-03** ✅ Quitar `except Exception: pass` en `MLflowExecutor.validate`; los `ValidationError` críticos se propagan
- **F1-04** ✅ SageMaker `preprocess.py`: corregir `ComplianceRegistry.get` → `get_compliance` y la firma de `apply`; fallar si compliance no puede aplicarse
- **F1-05** ✅ Verificar `dataset.hash` en `godml run` cuando está fijado; error si no coincide. Con `provider: sagemaker` y hash fijado, emitir un warning explícito de que el hash no se verifica para datos en S3; documentarlo en "Upgrading from 1.3.x"
- **F1-06** ✅ Hash de PII con HMAC-SHA256 y llave desde `GODML_PII_KEY` (error en prod si falta). **Ajuste:** exigir `GODML_PII_KEY` siempre que compliance esté activo, en cualquier entorno; única excepción `GODML_ALLOW_INSECURE_PII_KEY=1` fuera de prod; el error indica cómo generar la llave (`secrets.token_hex(32)`); documentarlo en "Upgrading from 1.3.x"
- **F1-07** ✅ Detector de PII: heurística por nombre a nivel token (no substring), excluir la columna target, endurecer patrones de contenido (cvv, zip, coordenadas) → *tests con columnas `zip_code`, `hotel_id`, `plate`, `year`, `fare`*
- **F1-08** ✅ Deploy: mapeo de puertos `{port}:8000` o CMD que lea `$PORT`; `serve` sin `reload` fuera de dev
- **F1-09** ✅ `resolver.py`: recursión en listas de dicts e interpolación parcial (`"prefix-${X}"`)
- **F1-10** ✅ Umbrales con dirección: métricas tipo pérdida (`mse`, `rmse`, `mae`, `log_loss`) se evalúan con `<=`
- **F1-11** ✅ Server: reordenar features por `feature_names_in_` / `feature_names`; devolver `predict_proba` cuando exista
- **F1-12** ✅ `import godml` sin efectos colaterales: quitar filtros globales de warnings, creación de `logs/` al importar y `logging.basicConfig`; no modificar `os.environ` al importar godml (variables de TensorFlow); `get_logger()` sin handlers propios (`NullHandler`): solo la CLI configura la salida
- **F1-13** ✅ Corregir `_is_safe_absolute_path` y `validate_model_path` con `Path.is_relative_to`
- **F1-14** ✅ README honesto: quitar GDPR/HIPAA/SOX, corregir ejemplos de notebook/advisor/tune, agregar `target` al quick start y a `godml init`; corregir `godml/utils/README_TEMPLATE.txt` (no imponer badge MIT a proyectos de usuarios, Python 3.11+); corregir nombres de assets en la sección de verificación del README (`multiple.intoto.jsonl`, `sbom.cyclonedx.json`)
- **F1-15** 🟨 Publicar 1.4.0 con CHANGELOG; las notas de 1.4.0 abren con "Upgrading from 1.3.x": compliance no soportado aborta, validaciones de gobernanza ahora bloquean, y cómo revisar/borrar datasets crudos en runs de MLflow 1.x; documentar también que SageMaker nunca aplicó compliance, que ahora se rechaza al validar, y el workaround: aplicar compliance localmente, subir los datos ya procesados a S3 y ejecutar SageMaker sin la clave `compliance`, hasta la imagen oficial de 2.0
- **F1-16** ✅ Helper único `is_text_like(dtype)` para detectar columnas de texto (object y str de pandas 3); usarlo en providers/mlflow.py, sagemaker preprocess.py y advisor_orchestrator.py
- **F1-17** ✅ MLflowExecutor: al convertir MLFLOW_TRACKING_URI file: → sqlite:, crear el directorio padre y registrar la conversión en log
- **F1-18** ✅ `sagemaker/scripts/evaluate.py`: mover la lógica de nivel módulo a `main()` bajo `if __name__ == '__main__':` (regla de tests herméticos); corregir el filtro anti path-traversal del tarball con `Path.resolve()` + `is_relative_to` (hoy `startswith` deja pasar rutas hermanas como `model2/`)
- **F1-19** ✅ (después de F1-12) Fixture de sesión que falle la suite si algún test crea archivos fuera de `tmp_path`
- **F1-20** ✅ CLI robusta a encoding: quitar emojis del texto de `--help` y configurar stdout/stderr con `errors="replace"` en el entrypoint de la CLI → *test: `godml --help` con `PYTHONIOENCODING=ascii` no falla*
- **F1-21** ✅ `deploy_template`: no registrar valores del input en logs (solo forma/columnas)
- **F1-22** ✅ Test de la condición de métricas de pérdida en `step_builder.py` (unitario o con SDK de SageMaker en un job de test)
- **F1-23** ✅ Extra `aws`: `sagemaker<3`. El SDK v3 (lo que instalaba `godml[aws]` con `<4`) eliminó `sagemaker.workflow`, `sagemaker.processing` e `image_uris`; el executor de SageMaker estaba roto en instalaciones nuevas. Portar a v3 → F4-07
- **F1-24** 🟨 Smoke test post-publicación: job que tras publicar instala `godml[all]==<versión>` desde PyPI en entorno limpio y corre `godml --help`, `godml init demo`, `godml run` y el caso sin `GODML_PII_KEY` (error esperado). La promoción a final requiere este job en verde. Correrlo contra 1.4.0rc1

### F2 — Arquitectura 2.0 (2.0.0a1)

- **F2-01** ⬜ Crear layout por pilares (§2.1) con shims de compatibilidad para imports 1.x (`DeprecationWarning`)
- **F2-02** ⬜ Spec v2 en Pydantic con `extra="forbid"`; exportar JSON Schema a `schemas/godml-v2.json`
- **F2-03** ⬜ Loader único (reemplaza `config_service/loader.py` y `core_service/parser.py`) con soporte de herencia `godml.defaults.yaml` → equipo → modelo
- **F2-04** ⬜ Carga de spec v1 con conversión interna a v2 (base para `godml migrate`)
- **F2-05** ⬜ Registro de plugins vía entry points (executors, políticas, estimadores)
- **F2-06** ⬜ Jerarquía de errores (`GoDMLError`, `SpecError`, `PolicyViolation`, `MissingExtra`, …) y códigos de salida de CLI documentados
- **F2-07** ⬜ Logging de librería correcto (`getLogger("godml")` + `NullHandler`); salida bonita solo en la CLI
- **F2-08** ⬜ CLI con imports perezosos por pilar; `godml --help` arranca en menos de 300 ms solo con core
- **F2-09** ⬜ Test de modularidad: por cada extra, entorno limpio con solo ese extra y sus tests pasando
- **F2-10** ⬜ Sacar mlflow del core al extra `train` (hoy mlflow-skinny arrastra fastapi/uvicorn a `pip install godml`); el core no debe importarlo
- **F2-11** ⬜ Agente de triage con `anthropics/claude-code-action`: etiquetado por pilar y tipo, solicitud de info faltante en bugs, revisión de PRs contra las reglas de CLAUDE.md (ID de tarea, CHANGELOG, tests, sin `except: pass`) y resumen de PRs de Dependabot. Requiere secreto `ANTHROPIC_API_KEY`

### F3 — Pilar Govern (2.0.0a1)

- **F3-01** ⬜ Motor de políticas con gates `pre-train`, `post-train`, `pre-deploy`; resultado estructurado (pass/fail/waived + razón)
- **F3-02** ⬜ Política PCI-DSS migrada al motor; arquitectura lista para nuevas políticas (sin anunciar GDPR/HIPAA hasta implementarlas); endurecer patrones ambiguos: Luhn para `card_number`, `phone_us` y `ssn_compact` (hoy aceptan cualquier número de 10/9 dígitos)
- **F3-03** ⬜ Verificación de datos: sha256, esquema esperado y conteo mínimo de filas; verificar el hash de datos en S3 (checksum SHA-256 de S3 o descarga). En 2.0 un hash declarado que no puede verificarse es error
- **F3-04** ⬜ Reglas por entorno: en `prod`, hash fijo, owner y aprobación obligatorios
- **F3-05** ⬜ `godml validate <dir>` sobre repo central completo, con salida para CI (JUnit/SARIF)
- **F3-06** ⬜ Reporte de gobernanza por run (JSON + Markdown) adjunto al bundle

### F4 — Pilar Train (2.0.0a2)

- **F4-07** ⬜ Executor SageMaker: imagen con godml instalado, hiperparámetros desconocidos rechazados en validación
- **F4-01** ⬜ Estimador por import path (`xgboost.XGBClassifier`) además de alias de catálogo
- **F4-02** ⬜ Preprocesamiento como `sklearn.Pipeline` persistido junto con el modelo (elimina training-serving skew)
- **F4-03** ⬜ Corrección de multiclase y regresión en catálogo (XGBoost, RandomForest, Logistic)
- **F4-04** ⬜ `params` libres validados contra la firma del estimador (no se pierden en silencio)
- **F4-05** ⬜ Bring-your-own-model: registrar un `.pkl` existente con su pre/post bajo el mismo contrato
- **F4-06** ⬜ Executor local (sin MLflow) y executor MLflow como plugins; crear el experimento con `artifact_location` junto al store sqlite (hoy cae en `./mlruns` relativo al cwd)
- **F4-08** ⬜ Reintentos reales (solo errores transitorios) o eliminar `max_attempts`
- **F4-09** ⬜ LSTM movido a `train-dl`; eliminar `run_pipeline.py` muerto
- **F4-10** ⬜ Compatibilidad con scikit-learn 1.8 (`multi_class` retirado)
- **F4-11** ⬜ `tune_model` con columnas de texto: codificarlas (o usar el Pipeline de F4-02) en lugar de fallar en todos los fits
- **F4-12** ⬜ Migrar el extra `sagemaker` a 3.x (≥3.8.0): adaptar el provider (`processing`, `workflow`, estimadores `SKLearn`/`XGBoost`, `image_uris`) y quitar de `.safety-policy.yml`/SECURITY.md el ignore `SFTY-20260305-71051` (vence 2027-01-23)

### F5 — Pilar Serve (2.0.0b1)

- **F5-01** ⬜ Formato de bundle: `manifest.json` (hashes, versión, firma de entrada/salida), modelo, pipeline, pre/post, baseline, reporte de gobernanza
- **F5-02** ⬜ `godml bundle build|inspect|verify`
- **F5-03** ⬜ Runtime único (reemplaza los 3 servidores actuales); lifespan en lugar de `on_event`; códigos de error correctos: errores del modelo son 5xx (la plantilla devuelve 400 y Prometheus los cuenta como `client_error`)
- **F5-04** ⬜ Variantes A/B y canary con pesos declarados y header de variante en la respuesta
- **F5-05** ⬜ `godml deploy`: Dockerfile generado, puertos correctos, usuario non-root, healthcheck
- **F5-06** ⬜ Gate `pre-deploy` obligatorio antes de servir en `prod`

### F6 — Pilar Observe (2.0.0b1)

- **F6-01** ⬜ Nombre y versión de modelo tomados del manifiesto del bundle
- **F6-02** ⬜ Métricas y drift etiquetados por variante A/B
- **F6-03** ⬜ Soporte multi-worker de Prometheus (modo multiprocess)
- **F6-04** ⬜ Histograma de predicción sobre probabilidades; métricas separadas para clase predicha
- **F6-05** ⬜ OpenLineage con `datetime.now(timezone.utc)`; eventos por run y por deploy
- **F6-06** ⬜ Dashboards Grafana actualizados (selector de variante) y sin credenciales por defecto en ejemplos

### F7 — Pilar Tools (2.0.0b2)

- **F7-01** ⬜ `godml init` con plantillas para cada pilar (`--template train|serve|repo-central`) que funcionen al primer `godml run`
- **F7-02** ⬜ Notebook API alineada con la spec v2 (mismos objetos que la CLI)
- **F7-03** ⬜ Recetas de preprocesamiento integradas al `sklearn.Pipeline` del pilar Train
- **F7-04** ⬜ `godml migrate` v1 → v2 con reporte de cambios
- **F7-05** ⬜ Advisor LLM y RAG movidos a `tools-ai`, con API que devuelve datos (no solo imprime)
- **F7-06** ⬜ Retirar Cython (D4): eliminar `.pyx`/`setup.py` de la extensión y dejar la implementación pura en Python, con benchmark que confirme rendimiento aceptable

### F8 — Empaquetado y distribución (2.0.0rc1)

- **F8-01** ⬜ Extras por pilar en `pyproject.toml` (§2.2) con rangos de versión probados; quitar `pymysql` del extra `data` (ningún módulo lo usa)
- **F8-02** ⬜ Lockfile reproducible con hashes (pip-tools `--generate-hashes` o uv)
- **F8-03** ⬜ Receta conda multi-output `noarch: python` (§2.3), probada localmente con rattler-build
- **F8-04** ⬜ Verificar disponibilidad en conda-forge de cada dependencia; documentar las que queden solo en PyPI
- **F8-05** ⬜ PR a `conda-forge/staged-recipes`; después mantener el feedstock (bot de actualización)
- **F8-06** ⬜ Release: SBOM y firmas adjuntos al GitHub Release (no solo como artifact del workflow)
- **F8-07** ⬜ Imágenes Docker oficiales por uso: `godml-serve` y `godml-train`

### F9 — Docs, ejemplos y lanzamiento (2.0.0)

- **F9-01** ⬜ Sitio de documentación con una sección por pilar (instalación + guía + referencia)
- **F9-02** ⬜ Ejemplos ejecutables: un ejemplo por pilar + "repo central con N modelos"
- **F9-03** ⬜ Guía de migración 1.x → 2.0
- **F9-04** ⬜ README nuevo centrado en los 5 pilares
- **F9-05** ⬜ Serie de publicaciones en LinkedIn (ver §6)
- **F9-06** ⬜ Release 2.0.0 en PyPI y conda-forge

---

## 5. Definición de "terminado" para 2.0.0

- Cero bugs P0/P1 conocidos abiertos
- CI bloqueante: ruff, mypy, bandit, pip-audit, tests por extra y matriz de Python
- Cobertura **real, sin exclusiones** ≥ 80 % en `core` y `govern`, ≥ 70 % en el resto
- Cada extra se instala y prueba de forma aislada
- `pip install godml` (solo core) instala menos de 10 dependencias transitivas directas
- README y docs sin funcionalidades no implementadas
- Disponible en PyPI y conda-forge con los mismos pilares

---

## 6. Comunicación (LinkedIn)

| # | Momento | Tema |
|---|---|---|
| 1 | Al cerrar F1 | "GoDML 1.4.0: más seguro, fail-closed" + anuncio del camino a 2.0 |
| 2 | Al cerrar F2 | Los 5 pilares y la instalación por pilar |
| 3–7 | Al cerrar cada pilar | Un post por pilar con caso de uso y snippet |
| 8 | F9 | Lanzamiento 2.0 + conda-forge + historia del repo central de 500+ modelos |

---

## 7. Log de estado

Claude Code agrega una entrada por sesión (la más reciente arriba).

| Fecha | Tareas | Resultado | Notas / bloqueos |
|---|---|---|---|
| 2026-10-30 | F1-15 | 🟨 **1.4.0rc1 publicada en PyPI.** El usuario activó la facturación de la organización DAGMALIA en PyPI; rerun del job "Publish to PyPI" (run 41004513742, intento 2) en verde por OIDC (`id-token: write`, environment `pypi`, sin token guardado). Trusted Publisher vigente: la procedencia de PyPI (`/integrity/.../provenance`) registra publisher GitHub `DAGMALIA/godml`, workflow `release.yml`, environment `pypi`. sha256 en PyPI = los del Release verificados con SLSA (wheel `3582658…04d6`, sdist `148c8da…e994`). `pip install godml==1.4.0rc1` en venv limpio → `godml 1.4.0rc1`; `godml --help` exit 0, también con `PYTHONIOENCODING=ascii` | Pendiente: autorización del usuario para **1.4.0 final** (merge del PR #92 a `main` con versión `1.4.0`) |
| 2026-10-30 | F1-15 | ⛔ rc1 publicada en GitHub, **no en PyPI**. `safety_scan.yml` (run 41004240580, commit `a55f7fa`): gate de Safety OK (3 ignores revisados), tag `v1.4.0rc1` empujado con `RELEASE_PAT`. `release.yml` (run 41004513742): build, CycloneDX, SLSA L3 y GitHub Release (**pre-release**) en verde; **Publish to PyPI falló: "400 Organization account owning this project is inactive"** (la organización de PyPI dueña de `godml` está inactiva: facturación o intervención de admins). Verificado: `slsa-verifier` v2.7.1 PASSED para wheel y sdist (source-tag v1.4.0rc1); Cosign `verify-blob` del SBOM SPDX OK (identidad `safety_scan.yml@refs/heads/release/1.4.0`); CycloneDX 1.5 (124 componentes) en el Release; wheel del Release en venv limpio → `1.4.0rc1`, `godml --help` exit 0 también con `PYTHONIOENCODING=ascii`. PyPI sigue en 1.3.0 | Usuario: reactivar la organización en PyPI (support+orgs@pypi.org o facturación); luego `gh run rerun 41004513742 --failed` publica el mismo wheel verificado y se prueba `pip install godml==1.4.0rc1`. 1.4.0 final solo con autorización del usuario |
| 2026-10-30 | F1-15, F4-12 (alta) | ⛔→🟨 Primer `workflow_dispatch` de `safety_scan.yml` (run 41001790646) **bloqueado por el gate**: con todos los extras (165 dependencias) Safety reporta `SFTY-20260305-71051` en sagemaker 2.257.7 (JumpStart `search_hub()`; fix solo en 3.8.0). Falló antes del tag: nada publicado. godml no usa JumpStart. Usuario: ignore revisado (vence 2027-01-23) en `.safety-policy.yml` + SECURITY.md; migración a sagemaker 3.x → **F4-12** | Relanzar el release de rc1 |
| 2026-10-30 | F0-16 | ✅ La política de Safety Platform no se puede quitar: el modo plataforma lo activa el servidor, `safety scan` siempre usa la política de la nube y, al borrar el codebase, el siguiente scan lo recrea con una política por defecto; además la plataforma rechaza IDs `SFTY-...` ("validation failed") y `scan` solo empareja ignores por ID literal; `safety check` (deprecado) sí prefiere la política local, pero solo acepta IDs numéricos. Decisión del usuario: **gate en el repo**. CI corre Safety 3.3.1 directo (sin `pyupio/safety-action`), guarda el JSON y `.github/scripts/safety_gate.py` falla si hay un hallazgo que no esté en `.safety-policy.yml` con `expires` vigente (ignora lo que Safety haya marcado como ignorado), si Safety no termina (exit ≠ 0/64), si falta el reporte o si falta algún paquete del `pip freeze`. Sigue bloqueante, sin `continue-on-error`; badges sin cambios. Tests del gate en `test_safety_policy.py` (19). CI del PR #92: 111 dependencias, 2 hallazgos aceptados, **17/17 en verde**. 609 tests locales | En Safety Platform quedó guardado el ignore `71782` (skops); da igual, el gate decide. **F0 cerrada** |
| 2026-10-26 | F0-16 | 🟨 Hallazgo: el Safety de 1.x **nunca auditó nada**: `safety scan` (CLI 3.3.1 del action) escaneaba los rangos de `pyproject.toml`, la política de Safety Platform ignora requisitos sin fijar ("92 found, 92 ignored due to policy"), los `--ignore` eran opciones de `safety check` (sin efecto en `scan`) y corría con `continue-on-error`. Hecho: Safety bloqueante en `ci.yml` (audit) y `safety_scan.yml`, sobre un `pip freeze` fijado del entorno instalado, con `--policy-file .safety-policy.yml`; badge enlazado al resultado real; test de sincronía política↔SECURITY.md↔workflows. Primer CI real: 111 dependencias, **2 hallazgos HIGH sin fix** (mlflow `SFTY-20240604-95861`/CVE-2024-37058, skops `71782`/CVE-2024-37065); ninguno de los 15 IDs de 1.x aplica a lo que resuelve CI → los 15 se eliminan (la revalidación previa con la base pública gratuita estaba desactualizada: marcaba 8 IDs de mlflow como vigentes). El usuario aprobó los 2 nuevos como ignores revisados (vencen 2027-01-23) y que **el repo mande** | Pendiente del usuario: eliminar la política del proyecto `godml` en Safety Platform; el código del CLI (`resolve_policy`) siempre prefiere la de la nube y hoy ignora `.safety-policy.yml`. Hasta entonces el job `audit` falla. `RELEASE_PAT` rotado (2026-10-26 01:40 UTC) |
| 2026-10-25 | F1-15 | ⛔ PR #92 (`release/1.4.0` → `main`, versión `1.4.0rc1`). Primer CI en Linux encontró 2 bugs que en Windows no se veían: (1) **`model_loader` importaba código desde fuera del proyecto si `models/` era un symlink** (la base se resolvía siguiendo el enlace) → base = `resolve(proyecto)/models`; el test usa junction en Windows y ya no se salta; (2) `tarfile.extractall` sin `filter` → `DeprecationWarning` en 3.12/3.13 (error por la política de F0-11) → `filter="data"` cuando existe. Además `release.yml` marca tags PEP 440 (`aN`/`bN`/`rcN`) como pre-release de GitHub. CI final: **17/17 checks en verde**, 590 tests en 3.11/3.12/3.13, 0 skips, cobertura 61.6 %. Publicación de rc1: `safety_scan.yml` por `workflow_dispatch` en `release/1.4.0` **falló en el checkout**: `RELEASE_PAT` inválido/vencido (actualizado por última vez 2026-06-28). **No se publicó nada** (sin tag `v1.4*`, sin GitHub Release, PyPI sigue en 1.3.0) | Bloqueo: el usuario debe rotar el secreto `RELEASE_PAT` (permiso `contents: write` para empujar el tag, y que dispare workflows). Sin eso también fallaría el release final desde `main`. Alternativa: empujar el tag `v1.4.0rc1` a mano (dispara `release.yml`: build, SLSA, Release, PyPI) pero sin el SBOM SPDX firmado de `safety_scan.yml` y dejando roto el camino oficial |
| 2026-10-25 | F1-22 (+ F1-23 seguimiento) | ✅ Dos niveles: (1) `tests/unit/test_sagemaker_register_condition.py` reemplaza los 4 módulos del SDK por grabadores y prueba `build_register_step` para mse/rmse/mae/log_loss (`LessThanOrEqualTo`) y auc/accuracy (`GreaterThanOrEqualTo`): con el código previo a F1-10 fallan los 4 de pérdida; (2) `tests/integration/test_sagemaker_sdk_contract.py` contra el **SDK real**: los 17 nombres que importa godml existen y la condición real serializa `LessThanOrEqualTo`/`GreaterThanOrEqualTo`. Nuevo extra `test-aws` (= `godml[aws]`) instalado por CI (`test`, `lint`, release) para que no se salte. Al reproducir el entorno CI con pip-audit: `sagemaker 2.243.2` con PYSEC-2026-3059/3060 → piso `sagemaker>=2.257.2,<3`; y `virtualenv` (de `pre-commit`) con 8 CVEs, cuyo fix exige `packaging>=26.3`, incompatible con sagemaker 2.257 (`packaging<25`) → **`pre-commit` sale de `dev`** (`pipx install pre-commit`). Entorno CI desde cero (sin caché): sagemaker 2.257.7, pip-audit limpio, 589 tests, mypy/ruff OK, cobertura 61.37 % | Sin el ajuste, el job de release (pip-audit bloqueante sobre dev+test) habría fallado. Nota para F0-04: pre-commit ya no se instala con `dev` |
| 2026-10-25 | F1-23 (nueva) | ✅ Hallazgo al verificar F1-22 con el SDK real: `pip install -e ".[aws]"` resolvía **sagemaker 3.27.0**, donde no existen `sagemaker.workflow`, `sagemaker.processing` ni `sagemaker.image_uris` (los 7 imports del executor fallan) → executor de SageMaker inutilizable para cualquier instalación nueva. Fix: `sagemaker>=2.200.0,<3`. Con 2.257.7 los imports funcionan y la condición real se construye bien (`mse`→`LessThanOrEqualTo`, `auc`→`GreaterThanOrEqualTo`). CHANGELOG: Fixed | AWS marca el SDK v2 como "on path of deprecation" (`SageMakerV2DeprecationWarning`); portar a v3 queda en F4-07 |
| 2026-10-25 | F1-21 | ✅ Test primero (`tests/unit/test_serving_no_input_logging.py`, ambos servidores, captura de todo el logger `GODML` con un valor centinela): la plantilla registraba `str(df)` (valores completos de cada request). Fix: solo `filas x columnas` y nombres de columnas. `deploy_service/server.py` ya no registraba inputs (test lo fija). CHANGELOG: Security (regenerar `deploy_service/` en proyectos previos) | — |
| 2026-10-25 | F1-06 (ajuste) | ✅ Tests reescritos primero (21 fallaban con la regla anterior). `pii_hash_key()`: `GODML_PII_KEY` obligatoria siempre que compliance se aplique, con **cualquier política** y en cualquier entorno; `GODML_ALLOW_INSECURE_PII_KEY=1` (solo el valor `1`) usa la llave de dev fuera de prod con warning, y en prod es error; los mensajes incluyen `secrets.token_hex(32)`. `PciDssCompliance.apply` resuelve la llave al inicio (falla antes de tocar datos). Suite: fixture autouse con llave de test en `conftest.py`. README (quick start, configuración, compliance) y `godml init` lo documentan; test del README lo exige. CHANGELOG: "Upgrading" + Security reescritos | Interpretación literal de "siempre que compliance esté activo": `mask_sensitive`/`drop_sensitive` también exigen la llave aunque no la usen. Como `godml init` genera `compliance: pci-dss`, el quick start ahora pide exportar `GODML_PII_KEY` |
| 2026-10-25 | Decisiones | Usuario: F1-06 exige `GODML_PII_KEY` con compliance activo en todo entorno (excepción `GODML_ALLOW_INSECURE_PII_KEY=1` fuera de prod); nuevas F1-21 y F1-22 antes del release; Luhn/phone/ssn → F3-02, `pymysql` → F8-01, `tune_model` texto → F4-11, códigos de error del server → F5-03. F1-15: PR a main con CI, luego **1.4.0rc1** como pre-release verificada; 1.4.0 final la autoriza el usuario | — |
| 2026-10-25 | F1-14 | ✅ README reescrito tras auditar cada afirmación contra el código: fuera GDPR/HIPAA/SOX, `GdprCompliance`, `GodmlNotebook.load_data/train_model/evaluate`, alias `xgb/rf/logreg`, proveedor "Local", "every run produces a signed trail", enlace a `CONTRIBUTING.md` (no existe), roadmap con versiones ya pasadas; corregidos notebook (`create_pipeline`/`train`/`save_model(model_name=...)`), `tune_model` (`metric="roc_auc"`, sin promesa de Optuna, features numéricas), advisor (`[advisor]`, imprime y devuelve `None`), modelos (+`linear_regression`, `lstm_forecast`), compliance (políticas reales, `GODML_PII_KEY`), extras (sin MySQL: no hay conector), CLI completa (`serve`, `calc-hash`, `dataprep`), assets reales del Release. `godml init` escribe `dataset.target`; ayuda de `deploy` con los entornos reales; `README_TEMPLATE` sin badge MIT, Python 3.11+, `target` y comandos reales (`calc-hash`, `--version`; `save_model` pasaba el nombre como modelo). Nuevo `tests/integration/test_readme.py`: **ejecuta** los ejemplos Python y el YAML (run MLflow real), valida comandos CLI/extras/tipos de modelo y prohíbe GDPR/HIPAA/SOX. Ese test destapó 2 bugs: `tune_model` falla con columnas de texto (ejemplo ajustado) y **RandomForest no se podía registrar en MLflow reciente** (commit `92cec64`). 544 tests en ambos entornos, cobertura 61.16 % | El bloque del advisor no se ejecuta en el test (requiere gpt4all + modelo local); lista explícita `NOT_EXECUTED`. `pymysql` en el extra `data` no lo usa ningún módulo (F8-01). `model_registry.py` importa el LSTM (Keras) a nivel módulo (F4-09) |
| 2026-10-25 | F1-20 | ✅ Tests primero (`tests/unit/test_cli_encoding.py`: subprocess con `PYTHONIOENCODING=ascii` y `cp1252`, `--help` y `dataprep --help`, cwd temporal; más un chequeo estático de que ningún texto de ayuda tiene emojis): fallaban los 5. Fix: `godml_cli.main()` reconfigura stdout/stderr con `errors="replace"` antes de configurar logging; se quitó el 🧩 (y la raya) del `help` de `dataprep`. Verificado a mano: `godml --help > archivo` en el venv limpio sale con 0 (antes 1 con `UnicodeEncodeError`). 531 tests en ambos entornos, cobertura 60.47 % | Quitar emojis no basta para ASCII: los textos tienen acentos, que solo se salvan con `errors="replace"`. Los logs de la librería y de la CLI siguen con emojis (se reemplazan por `?` en terminales sin UTF-8) |
| 2026-10-25 | F1-11 | ✅ Tests primero (`tests/unit/test_serving_features.py`, `TestClient` contra **ambos** servidores, sklearn y Booster reales): con las claves JSON en otro orden, sklearn respondía 500 ("same order as in fit") y el Booster "feature_names mismatch"; una clave extra rompía la request; nunca había probabilidades. Fix: `godml/utils/serving.py` (`expected_features` vía `feature_names_in_`/`feature_names`, `align_features` reordena e ignora extras, `MissingFeaturesError`→400, `predict_with_proba`) usado por `deploy_service/server.py` y la plantilla; respuesta suma `probabilities` sin cambiar `prediction`. 526 tests en ambos entornos, cobertura 60.17 % | Hallazgos en la plantilla (F5-03): (1) registra el input completo con `godml_logger.info(str(df))` → **PII de cada request en los logs**; (2) su `except` interno convierte cualquier error del modelo en 400, que Prometheus cuenta como `client_error` |
| 2026-10-25 | F1-08 | ✅ Tests primero (`tests/unit/test_deploy_ports.py`, Docker y uvicorn simulados): `docker run -p {port}:{port}` con el contenedor escuchando siempre en 8000 → qa (8001) y prod (80) inaccesibles; `serve` con `reload=True` en todo entorno. Fix: `-p {port}:CONTAINER_PORT` (8000) y se deja de pasar `-e PORT=...` (nadie lo leía); `reload` solo con `environment == "dev"`. Test de sincronía: `CONTAINER_PORT` coincide con CMD `--port`, `EXPOSE` y healthcheck de `DOCKERFILE_TEMPLATE.txt`. 516 tests en ambos entornos, cobertura 59.35 % | Se eligió el mapeo a puerto fijo y no un CMD que lea `$PORT`: mantiene alineados `EXPOSE` y el healthcheck sin shell en el CMD. Los `ENVIRONMENTS` de `deploy_service/env_config.py` (`reload`, `port`) no los usa ningún comando (deuda para F5-05) |
| 2026-10-25 | F1-09 | ✅ Tests primero (`tests/unit/test_resolver_interpolation.py`, incluye 2 de punta a punta con `load_pipeline`, que fallaban con el resolver viejo). El resolver no recursaba en listas de dicts/listas (`governance.tags`, `metrics` quedaban con `${VAR}` literal) y sustituía el string completo por la variable (`s3://${BUCKET}/data.csv` → solo el bucket; solo la primera variable). Fix: `_resolve` recursivo sobre dict/list y `re.sub` por cada `${VAR}`/`${VAR:default}`; no muta la entrada. Decisión: valor que es exactamente `${VAR}` sin definir → `None` (1.x); dentro de un string más largo → `ConfigurationError` (evita rutas que pierden un segmento en silencio). Los dos loaders ya lo envuelven en `ConfigurationError`. 508 tests en ambos entornos, cobertura 57.88 %. CHANGELOG: Fixed | — |
| 2026-10-25 | F1-10 | ✅ Tests primero (`tests/unit/test_metric_thresholds.py`). La dirección "mayor es mejor" estaba en 3 sitios: gate de registro de `MLflowExecutor.run`, ícono ✓/✗ de `print_metrics_table` (CLI) y `ConditionGreaterThanOrEqualTo` de SageMaker; con `mse: 0.5`, error 0.1 fallaba y 2.0 pasaba. Fix: `monitoring_service/thresholds.py` (Python puro: `LOWER_IS_BETTER` = mse, rmse, mae, log_loss; `passes_threshold`, `failed_thresholds`, `register_condition_name`) usado en los 3 sitios; `validate_metrics` deja `log_loss` sin límite [0,1]. 495 tests en ambos entornos, cobertura 57.76 %. CHANGELOG: Fixed + "Upgrading" | El cambio en `step_builder.py` (`ConditionLessThanOrEqualTo` vía `getattr`) **no se ejecutó**: el SDK de SageMaker no está en ningún entorno de test; solo se verificó que el módulo parsea y que el nombre de la condición es correcto. `rmse` y `log_loss` hoy no se calculan (si se configuran, se advierte "no fue calculada") |
| 2026-10-25 | F1-07 | ✅ Tests primero (`tests/unit/test_pii_false_positives.py`): las 10 columnas comunes probadas (`hotel_id`→phone por "tel", `plate`/`latency_ms`→coordinates por "lat", `tip`/`description`→ip, `year`/`fare`→cvv, `amount`→zip, `score`→coordinates, `filename`→name) salían como PII y `drop_sensitive` las eliminaba. Fix: `name_tokens`/`name_has_hint` (token completo, snake/camelCase, pistas compuestas contiguas) en `PiiDetector` e `is_pii_column`; `NAME_CONFIRMED` = cvv, zip_code, postal_mx, coordinates (solo con nombre que lo confirme); `cvv` antes que `card_number` en las pistas; expiración exige `/`; `exclude_columns` en `PciDssCompliance`/`ComplianceEngine.apply`, usado con el target en `run_pipeline_preprocessing` y en el script de SageMaker. 2 tests viejos (`test_detects_zip_code`, `test_detects_cvv`) codificaban la detección solo por contenido: actualizados al nuevo contrato (con nombre → detecta; sin nombre → `unknown`). 479 tests en ambos entornos, cobertura 57.52 %. CHANGELOG: Fixed + "Upgrading" | Quedan patrones ambiguos fuera del alcance: `card_number` sin Luhn (timestamps en ms de 13 dígitos cuentan como tarjeta), `phone_us` acepta cualquier número de 10 dígitos, `ssn_compact` cualquier número de 9 dígitos → candidatos para F3-02 |
| 2026-10-25 | F1-06 | ✅ Tests primero (`tests/unit/test_pii_hmac.py`): `hash_sensitive` era SHA-256 **sin llave** truncado a 12 hex (reversible por fuerza bruta/diccionario en tarjetas y emails) e ignoraba cualquier llave. Fix: `compliance_utils.hmac_truncated` + `pii_hash_key()` (lee `GODML_PII_KEY` al aplicar; con `GODML_ENV` prod/production y sin llave → `ComplianceError`; fuera de prod → llave de dev **pública** `DEV_PII_KEY` + warning una vez por proceso). `hash_sha256`/`hash_truncated` se conservan (API pública). Aplica a PCI-DSS en `godml run`, dataprep y SageMaker. 450 tests en ambos entornos, cobertura 57.37 %. CHANGELOG: Security + "Upgrading" (los valores hasheados cambian) | **Decisión tomada, revisar:** sin llave fuera de prod se usa una llave de dev fija (estable entre entrenamiento y serving) en vez de fallar; como `GODML_ENV` vale `dev` por defecto, quien no configure nada recibe hashes no protegidos (con warning). Alternativa: exigir la llave en todo entorno salvo opt-in explícito |
| 2026-10-25 | F1-13 | ✅ Tests primero (`tests/unit/test_path_containment.py`): un directorio hermano con el mismo prefijo (`proj-evil`) pasaba como dentro del proyecto. Además de las 2 funciones del plan, mismo patrón en **`templates/deploy_template/server.py`** (se copia a proyectos de usuarios) y en **`model_service/model_loader.py`** (importa un `.py` local: ejecución de código). Fix: `Path.resolve()` + `is_relative_to` en los 4 sitios (stdlib, sin helper nuevo para que la plantilla no dependa de godml nuevo); `_is_safe_absolute_path` resuelve cwd/home en cada llamada (antes al importar: congelaba el cwd/home del primer import, lo que el propio test demostró) y su `except` pasó de `Exception` a errores de `resolve()`. `filterwarnings`: el ignore de `on_event` cubre también la plantilla (F5-03). 440 tests en ambos entornos, cobertura 57.12 %. CHANGELOG: Security, con aviso de regenerar `deploy_service/` | El test del symlink en `models/` se salta en Windows (sin privilegio para crear enlaces); corre en el CI Linux. Proyectos generados antes de 1.4.0 conservan la plantilla vulnerable: mencionar en notas de F1-15 |
| 2026-10-25 | Plan | F1-20 agregada. Orden acordado para el resto de F1: F1-13 → F1-06 → F1-07 → F1-10 → F1-09 → F1-08 → F1-11 → F1-20 → F1-14 → F1-15 | — |
| 2026-10-25 | F1-18 | ✅ `sagemaker/scripts/evaluate.py` reestructurado: `extract_model_archives` / `compute_metrics` / `main(model_dir, test_dir, out_dir)` bajo `if __name__ == '__main__'`; nada corre al importar. Filtro del tarball con `Path.resolve()` + `is_relative_to`, y rechazo de symlinks/hardlinks (antes no se revisaban). Tests primero (`tests/unit/test_sagemaker_evaluate.py`, con `os.makedirs` interceptado al importar para no tocar `/opt/ml`): rojo por ejecución al importar; demostrado aparte que el `startswith` viejo aceptaba `../model_evil/x.txt`. Auditoría AST: los 4 scripts de SageMaker cumplen la regla. 433 tests en ambos entornos, cobertura 56.93 %. CHANGELOG: Security | — |
| 2026-10-25 | F1-19 | ✅ Fixture de sesión `hermetic_tests` (autouse, `tests/conftest.py`) con `tests/hermetic.py`: foto (ruta → mtime) del repo al inicio y al final; falla la sesión si se **creó o modificó** cualquier archivo (excluye `.git`, cachés, `*.egg-info` y salida de pytest-cov). Tests de la lógica (`tests/unit/test_hermetic_guard.py`) + prueba punta a punta con un test temporal que escribía en el repo: `ERROR at teardown` y exit 1 (probe eliminado). Suite completa con la guardia: 425 tests en ambos entornos, sin violaciones (tras F1-12 ya no se escribe `logs/godml.log`). Recorrido del repo: ~0.02 s | Alcance: vigila el repo (cwd de pytest, donde caen las rutas relativas). Escrituras a rutas absolutas fuera del repo (p. ej. `/opt/ml`) no se detectan; las cubre la regla de scripts bajo `main()` (F1-18) |
| 2026-10-25 | F1-12 | ✅ Test primero (`tests/unit/test_import_side_effects.py`, subprocess con cwd temporal): importar godml creaba `logs/`, ponía 2 handlers propios y cambiaba env vars. Fix: `__init__.py` sin `os.environ` ni `filterwarnings`; `get_logger()` = `getLogger` + `NullHandler`; nueva `configure_cli_logging()` (consola + `logs/godml.log`, idempotente) llamada solo en `godml_cli.main`, que además fija las env de TF con `setdefault` antes de importar; sin `basicConfig` en `notebook_api/pipeline.py`. Hallazgo resuelto: `utils/predict_safely.py` importaba **tensorflow.keras y lightgbm a nivel módulo** (vía `providers/mlflow.py`), lo que cambiaba `TF2_BEHAVIOR`/`KMP_*` y hacía que un TF roto tumbara `godml --help`; ahora detecta esos modelos por `sys.modules` sin importarlos. Verificado: `godml --help` arranca en el entorno local (antes ImportError), `calc-hash` escribe `logs/godml.log`. 422 tests en ambos entornos, cobertura 55.90 %. CHANGELOG: "Upgrading" (logging silencioso fuera de la CLI) + Fixed | scikit-learn fija `KMP_DUPLICATE_LIB_OK`/`KMP_INIT_AT_FORK` al importarse; es de la dependencia, no de godml (el test importa las deps del core antes de medir). Preexistente: `godml --help` falla con `UnicodeEncodeError` (emoji 🧩) cuando stdout no es UTF-8 (Windows con salida redirigida/CI); idéntico con el código anterior |
| 2026-10-25 | Plan, F1-05 | ✅ Plan: F1-18 (incluye path-traversal de `evaluate.py`), F1-19, ajustes de F1-05, F1-12 (sin `os.environ`, `NullHandler`) y F3-03. F1-05, tests primero (`tests/unit/test_dataset_hash.py`): con hash fijado que no coincide, `godml run` **llegaba a entrenar**. Fix: `compliance_service/dataset_integrity.py::verify_dataset_hash` (hex sha256, acepta mayúsculas y `sha256:`; `auto`/vacío se omite; mensaje con ambos hashes y `godml calc-hash ... --update-yaml`), llamado en `MLflowExecutor.run` antes de usar los datos; `DatasetIntegrityError`. SageMaker: warning explícito de que el hash no se verifica para S3 (antes de `_require_aws`). CHANGELOG: nueva sección **"Upgrading from 1.3.x"** con todos los cambios incompatibles hasta hoy (F1-15 la completa). 417 tests en ambos entornos, cobertura 56.02 % | Hallazgo: en el entorno local `godml --help` falla porque la CLI importa `tensorflow.keras` de forma ansiosa y el TF local está compilado contra NumPy 1.x → un extra roto tumba toda la CLI (F2-08) |
| 2026-10-25 | Auditoría "Tests herméticos" | ⚠️ 2 violaciones existentes: (1) la suite escribe `logs/godml.log` **en el repo**: importar `monitoring_service.logger` crea un `RotatingFileHandler` a nivel módulo → se corrige con F1-12; (2) `sagemaker/scripts/evaluate.py` tiene 18 sentencias con lógica a nivel módulo (`os.makedirs`, lectura de env, extracción de `.tar.gz`); ningún test lo importa hoy. `preprocess.py`, `train_sklearn.py`, `train_xgboost.py` cumplen. Método: AST de los scripts + comparación de archivos del repo antes/después de la suite completa (402 tests); nada nuevo en `C:\opt` | Propuesta: guardia automática (fixture de sesión que falle si la suite crea archivos fuera de `tmp_path`) junto con F1-12, y `evaluate.py` bajo `main()` |
| 2026-10-25 | Plan + CLAUDE.md | ✅ Decisión del usuario: **no adelantar F4-07**; se mueve al inicio de F4. F1-15: "Upgrading from 1.3.x" documenta SageMaker sin compliance + workaround. F4-06: `artifact_location` junto al store sqlite. CLAUDE.md: nueva regla "Tests herméticos"; `sagemaker/scripts/preprocess.py` ya la cumple desde F1-04 (lógica en `main()` bajo `if __name__ == '__main__'`, sin trabajo al importar) | Auditoría de la regla en la fila siguiente |
| 2026-10-24 | F1-17 | ✅ Tests primero (`tests/unit/test_mlflow_tracking_uri.py`, cwd distinto para detectar rutas relativas). `_file_uri_to_sqlite()`: parsea con `urllib` (`url2pathname`), crea el directorio y registra la conversión en log. Hallazgo adicional: la lógica vieja (`replace('file:/','').lstrip('/')`) **quitaba la `/` inicial en POSIX** (`file:///home/u/mlruns` → `home/u/mlruns`, relativo al cwd: en Linux/CI la base caía en otro lugar) y no decodificaba `%20`. 402 tests en ambos entornos, cobertura 55.71 % | Con backend sqlite, MLflow usa `./mlruns` **relativo al cwd** como raíz de artefactos por defecto (no el directorio del store): los artefactos de un run quedan donde se ejecute `godml run`. Candidato: crear el experimento con `artifact_location` junto al store (F4-06) |
| 2026-10-24 | F1-04 | ✅ Hallazgo: además del `ComplianceRegistry.get` inexistente y la firma de `apply`, `step_builder.py` sube `preprocess.py` como `code=` a la **imagen sklearn estándar, que no trae godml**: el import fallaba siempre, el `except` lo volvía warning y **SageMaker entrenaba siempre con datos sin compliance**. `get_compliance()` además no acepta `policy`. Fix: (1) script reestructurado en `apply_compliance` / `encode_categoricals` / `main()` (antes corría todo al importarse, incluido `os.makedirs('/opt/ml/...')`); compliance vía `ComplianceEngine.apply` (respeta la política, fail-closed) y `RuntimeError` claro si godml no está en la imagen; codificación con `is_text_like` (F1-16; copia de respaldo para la imagen sin godml, con test de paridad); (2) `SageMakerExecutor.validate` rechaza `governance.compliance` antes de `_require_aws` y de lanzar jobs pagados. Tests primero (`tests/unit/test_sagemaker_preprocess.py` + 1 en `test_mlflow_validate.py`). 399 tests en ambos entornos, cobertura 55.58 %. CHANGELOG: Security con "Action required" | **Compliance + SageMaker queda inutilizable hasta F4-07** (imagen con godml); antes era peor: parecía funcionar y no protegía nada → considerar adelantar F4-07 o documentarlo en las notas de 1.4.0 (F1-15). Al crear el test, importar el script viejo creó `C:\opt\ml\processing\output\{train,test}` vacíos en la máquina de desarrollo; el borrado fue bloqueado por el control de seguridad y queda pendiente del usuario |
| 2026-10-24 | F1-15 (ajuste), F1-16, F1-17 (alta) | ✅ Plan: F1-16/F1-17 agregadas; F1-15 exige abrir las notas con "Upgrading from 1.3.x". F1-16: `godml/utils/dtypes.py::is_text_like(dtype)` (object o `str`/`string`, excluye categóricas; solo depende de pandas), tests primero (`tests/unit/test_dtypes.py`). Reemplaza el `_is_text` privado de `providers/mlflow.py` (4 usos) y el `select_dtypes(include=['object'])` del advisor, que bajo pandas 3 contaba 0 columnas de texto. El uso en `sagemaker/scripts/preprocess.py` entra con F1-04 (ese archivo se reestructura) | El conteo del advisor no tiene test propio (requiere mockear el LLM); el helper sí |
| 2026-10-24 | (hallazgo en F1-03) | ✅ **pandas 3**: en el venv tipo CI (pandas 3.1, mlflow 3.17, xgboost 3.2) fallaban los 3 tests de F1-02 — commiteados tras correrlos solo en local (pandas 2.3). Causa: pandas 3 infiere texto como `str`, y el executor solo reconocía `object` (`dtype == "O"`), así que el saneo post-compliance dejaba columnas de texto y XGBoost rechazaba el entrenamiento: **`godml run` con columnas de texto no funcionaba con pandas 3**, que `pandas<4` permite. Fix: helper `_is_text()` (object o string, excluye categóricas) en los 4 chequeos de `providers/mlflow.py`; test unitario del helper. 388 tests en local y en venv tipo CI, cobertura 54.94 % | Mismo patrón (`select_dtypes(include=["object"...])`) en `providers/sagemaker/scripts/preprocess.py` (F1-04) y `advisor_service/advisor_orchestrator.py` (solo conteo). Desde ahora: correr también en el venv tipo CI antes de commitear |
| 2026-10-24 | F1-03 | ✅ Test primero (`tests/unit/test_mlflow_validate.py`): owner en blanco, umbral `auc: 5.0` y batch sin `batch_output` **pasaban** `MLflowExecutor.validate` porque `validate_pipeline` lanza `ValidationError` y el `except Exception: pass` (`noqa: BLE001, S110`) se lo tragaba. Fix: la llamada queda fuera de `try`; los dos llamadores (`cli/commands/run.py`, `core_service/run_pipeline.py`) ya abortan ante cualquier excepción. `noqa` en `godml/`: 92 → 91 (y el único `S110` de `providers/mlflow.py`) | Ver fila siguiente: el fix de pandas 3 que destapó CI |
| 2026-10-24 | F1-02 | ✅ Test primero (`tests/integration/test_mlflow_dataset_artifacts.py`, run real de `MLflowExecutor` con store sqlite en `tmp_path`): confirmó que **el CSV de origen, con PII cruda, se subía a MLflow** aunque PCI-DSS estuviera configurado (`dataset_path` es el `uri` leído antes de compliance). Fix: se registra `dataset/dataset_metadata.json` (sha256 del origen, filas, tipos de columna; sin filas) y, solo con el nuevo `dataset.log_dataset: true` (default `false`), el dataset post-compliance. El test escanea todo lo que deja el run (DB sqlite, modelo, baseline) buscando valores PII crudos: ninguno. 379 tests, cobertura **53.89 %**. CHANGELOG: Security con "Action required" (runs 1.x pueden tener el dataset crudo en `dataset/`) | Bug aparte: `MLflowExecutor.__init__` convierte cualquier `MLFLOW_TRACKING_URI=file:...` a `sqlite:///<ruta>/mlflow.db` sin crear el directorio → `OperationalError` si no existe. El commit de código (`e5dffb6`) salió sin CHANGELOG/plan por un error de script; se completó en el commit siguiente |
| 2026-10-24 | D11, F2-10, ajuste F1-01 | ✅ Plan: D11 (hotfixes como **1.4.0**), "1.3.1" → "1.4.0" en tablero, encabezados F0/F1, F1-15 y §6 (también SECURITY.md); F2-10 agregada. F1-01: el error de estándar no soportado (`unsupported_standard()` en `compliance_service/errors.py`, usado por `ComplianceEngine` y el hook de dataprep) dice que los datos **nunca estuvieron protegidos**, cómo corregirlo (`pci-dss` o quitar la clave) y remite a CHANGELOG 1.4.0; tests endurecidos (fallaban antes del cambio). CHANGELOG: sección renombrada `[1.4.0] - Unreleased` con "Action required" | Sin cambiar: texto de D2 ("1.3.1 conserva `>=3.11,<3.14`") y de F0-09, y filas antiguas del log. El guard de versión (F0-02) exime `compliance_service/errors.py` (cita una release fija); sin eso, el bump a 1.4.0 en F1-15 lo habría hecho fallar |
| 2026-10-24 | F1-01 | ✅ Compliance fail-closed. Tests primero (`tests/unit/test_compliance_fail_closed.py`): 6 fallaban por el bug, incluido uno que probó que `MLflowExecutor.run` **entrenaba con datos que no pasaron compliance**. Fix: `ComplianceEngine.apply` lanza `ComplianceError` ante error del motor, import fallido o estándar no soportado; `run_pipeline_preprocessing` ya no captura y devuelve el df original; `MLflowExecutor.run` llama al preprocesamiento fuera del `try` amplio; el hook de dataprep (`_apply_compliance`) también rechaza estándares no soportados (antes `COMPLIANCE_SKIPPED` + df crudo). Lineage sigue best-effort. 376 tests (local y venv tipo CI), cobertura 48.38 → **50.81 %**; `noqa` en `godml/`: 95 → 92. CHANGELOG: sección Security | `ComplianceError` vive en `godml/compliance_service/errors.py` (hereda de `RuntimeError` por compatibilidad con el hook de dataprep) y no en `monitoring_service/logger.py`, porque importar ese módulo ejecuta `get_logger()` con `RotatingFileHandler` (efecto colateral, F1-12). Cambio de comportamiento: YAML con `compliance: gdpr` ahora falla → mencionar en notas de 1.3.1 (F1-15) |
| 2026-10-24 | F0-15, cierre F0 | ✅ Safety retirado (D10): paso `pyupio/safety-action` + 15 ignores + justificación eliminados de `safety_scan.yml`; ya no se instalan `safety` ni `pip-tools`, ni se sobrescribe `requirements.lock` con `pip freeze`; quitada la fila del resumen y el aviso de "riesgo residual MLflow aceptado". SECURITY.md: pip-audit como única auditoría, sin advisories ignorados. README: fila de CVE corregida (decía "Weekly", no hay schedule). **F0 cerrada**: F0-01…F0-15 ✅ | El archivo conserva el nombre `safety_scan.yml`: renombrarlo rompe la identidad Cosign (`--certificate-identity-regexp`) que documenta el README y el badge. El secreto `SAFETY_API_KEY` puede borrarse del repo en GitHub |
| 2026-10-24 | F0-13 | ✅ `moto[all]` eliminado: **ningún test usa moto** (ni boto3/sagemaker directo). `dev` = pytest, pytest-cov, pytest-mock, ruff, mypy, types-PyYAML, pre-commit; nuevos `test-serve` (`godml[api]` + httpx para `TestClient`) y `test-observe` (`godml[observability]`). CI (`test`, `lint`, release) instala `.[dev,test-serve,test-observe]`. Job `licenses`: `.[api,aws,advisor,data,observability]` (sin tensorflow) + gate `--fail-on` de copyleft fuerte (nombres exactos GPL/AGPL classifier + SPDX; partial-match descartado porque `GPL-3.0` ⊂ `LGPL-3.0`). Verificado en venvs limpios: `.[dev]` ya no trae boto3/moto/httpx/prometheus (122 paquetes vs 159 antes); `.[dev,test-*]`: 367 pasan, **0 skips**, cobertura 48.43 %; gate pasa con la lista real y falla (exit 1) con una licencia presente | fastapi y uvicorn siguen llegando **desde el core**: `mlflow` → `mlflow-skinny` 3.x los exige (también en `pip install godml` pelado) → F8-01 (mlflow al extra `train`). Hallazgo: en entorno limpio mypy fallaba por stubs de PyYAML faltantes (local pasaba por `types-PyYAML` instalado aparte), lo que habría roto el job `lint` de F0-04 → `types-PyYAML` agregado a `dev`. El gate no detecta expresiones compuestas (`MIT OR GPL-3.0-only`) |
| 2026-10-24 | F0-12 | ✅ Job `licenses` en `ci.yml`: instala `.[all]` + `pip-licenses==5.5.5` (5.0 dejaba 66 paquetes como UNKNOWN por no leer PEP 639), genera `LICENSE_REPORT.md` (resumen + tabla con URLs), lo sube como artifact `license-report` y al resumen del job. El `LICENSE_REPORT.md` manual (desactualizado: listaba lightgbm, omitía gpt4all/fastapi) sale del repo y queda en `.gitignore`. Script del paso probado localmente bajo `bash -eo pipefail` | Corrida local (env `dev`): sin licencias GPL; 2 paquetes sin licencia declarada en metadatos (`huey`, `skops`). Posible siguiente paso: gate `--fail-on` para copyleft fuerte |
| 2026-10-24 | F0-07 | ✅ SECURITY.md reescrito solo con hechos verificados: enforcement real por herramienta (Bandit HIGH bloquea; pip-audit bloquea; Safety no bloquea), los **15** IDs de Safety que ignora el workflow (el doc listaba 8) marcados como pendientes de revalidar (puestos para mlflow 3.4.0; CI hoy resuelve 3.17.2 y pip-audit no reporta nada), lockfile sin hashes y no usado por CI (antes decía "hash-verified"), artefactos reales del Release (wheel, sdist, `multiple.intoto.jsonl`, CycloneDX sin firmar; SPDX firmado solo como artifact del workflow), bind `0.0.0.0` por defecto (antes decía lo contrario), fecha de revisión 2026-10-24. Sección duplicada en español fusionada. Ignore `PYSEC-2024-230` (certifi, **sí** tenía fix en 2024.7.4) eliminado de ambos workflows; pip-audit sigue limpio sin él | Revalidar IDs de Safety requiere cuenta Safety. README: la sección de verificación cita `provenance.intoto.jsonl` y `sbom.spdx.json` como assets del Release, pero los reales son `multiple.intoto.jsonl` y `sbom.cyclonedx.json` → F1-14. Versión ES de SECURITY.md pendiente para F9 (D3) |
| 2026-10-24 | F0-06 | ✅ Eliminado `godml/deploy_service/.github/workflows/docker-ci.yml` (acciones sin pinear `@v3/@v4`, push a Docker Hub con tag `latest`). No se usaba: GitHub solo ejecuta workflows en `.github/` raíz y el scaffold copia desde `godml/templates/`, no desde `deploy_service`. No quedan otros `.github/` anidados | — |
| 2026-10-24 | F0-05 | ✅ Sin `|| true` en workflows: bandit `-lll` (HIGH) bloquea en `ci.yml`; pip-audit bloquea en `ci.yml` y `safety_scan.yml` (el resumen se sigue escribiendo; el paso sale con el código real, probado bajo `bash -e`). El reporte txt de bandit usa `--exit-zero` explícito (el bloqueo viene de la corrida SARIF). Job `audit` actualiza setuptools: la copia del runner (65.5.0) tiene 5 CVE y habría fallado sin ser dependencia de godml. Matriz D2: smoke test suma 3.13 (tests ya tenían 3.11–3.13). Verificado local: pip-audit limpio (exit 0) en venv tipo CI, bandit `-lll` exit 0 | Safety sigue con `continue-on-error` (requiere `SAFETY_API_KEY`; fuera del alcance de F0-05). `PYSEC-2024-230` ya no aparece aunque se quite el ignore → revisar en F0-07. `safety_scan.yml` sobrescribe `requirements.lock` con `pip list --format=freeze` en cada corrida → F0-07/F8-02 |
| 2026-10-24 | F0-04 | ✅ D9: commit de formateo aislado `94b0697` (112 archivos, solo `ruff format`) registrado en `.git-blame-ignore-revs`. Después, config: `[tool.ruff]` (E, W, F, `S110`, `BLE001`; sin E501) con la deuda existente marcada `# noqa: S110/BLE001` (95 en `godml/`, 7 en tests); 25 imports sin usar en tests corregidos; notebooks con ignores por archivo. `[tool.mypy]` gradual: 15 módulos con 46 errores previos en lista de deuda (`ignore_errors`), el resto se chequea. `.pre-commit-config.yaml` (ruff fijado por SHA v0.15.17 + mypy local) y ruff/mypy/pre-commit en `dev`. Job `lint` del CI usa la config del repo: `ruff check .`, `ruff format --check .`, `mypy`. Verificado: un archivo con `except Exception: pass` y error de tipos hace fallar ruff y mypy (exit 1); `pre-commit run --all-files` pasa; 367 tests | Inventario de deuda fail-closed: `git grep -n 'noqa: S110\|noqa: BLE001'`. El job `lint` anterior ya existía pero ignoraba la config del repo |
| 2026-10-24 | F0-14 | ✅ `.mailmap`: 6 identidades (incl. `arubior@aeromexico.com` y 2 noreply de GitHub) → una; `git shortlog -sne`: 123 commits del mantenedor + 22 de dependabot. Historial sin reescribir | La versión nueva del plan (D8, D9, F0-13) no llegó en el mensaje; D8/D9 registradas con lo dicho en chat, F0-13 queda como marcador. `.mailmap` aplica a git (log, shortlog, blame), no a la UI de GitHub |
| 2026-10-24 | F0-11 | ✅ Quitado `-p no:warnings`; `filterwarnings` convierte en error `DeprecationWarning`/`PendingDeprecationWarning` atribuidos a `godml(\..*)?`. Test `tests/unit/test_warning_policy.py` (los propios fallan, los de terceros siguen como warning; falla sin la config). El filtro destapó 2 usos reales de APIs obsoletas en código godml: `DataFrame.drop(inplace=True)` en `pci_dss.py` y `providers/mlflow.py` (pandas 3.1 `Pandas4Warning`, rompía 4 tests en CI) → corregidos con reasignación (mismo resultado, ya operaban sobre copia); FastAPI `on_event` en `deploy_service/server.py` → `ignore` puntual hasta F5-03. 367 tests pasan local (pandas 2.3) y en venv tipo CI (pandas 3.1, sklearn 1.9.1) | Por `stacklevel`, el filtro por módulo atrapa el uso de APIs obsoletas desde godml, pero **no** las deprecaciones que godml emita hacia código de usuario (se atribuyen al llamador). Para los shims de F2-01: usar una categoría propia (`GoDMLDeprecationWarning`) y filtrarla por categoría |
| 2026-10-24 | F0-10 | ✅ `omit` reducido a tests, `__pycache__` y `godml/templates/*` (scaffold que se copia a proyectos de usuario); también se quitó `except ImportError` de `exclude_lines` (ocultaba ramas de extras faltantes). Cobertura real **48.37 %** (1985/4104); `fail_under` 54 → **48**. Verificado en venv limpio con solo `.[dev]` (como CI): 48.4 %, mismo resultado | El plan estimaba ~41 %: esa cifra era de la rama vieja 1.2.4. Nota: `moto[all]` trae fastapi y boto3 de forma transitiva al extra `dev`. *(Corregido en F0-04: prometheus_client sí se instala en CI vía `dev` → `godml[observability]`; sus 29 tests corren.)* |
| 2026-10-24 | F0-03 | ✅ `godml.egg-info/` (6 archivos) sacado del índice; `.gitignore` ya tenía `*.egg-info/` (línea 8). No hay otros artefactos de build versionados; CI no lo referencia. Tras `pip install -e .`, `git status` queda limpio | — |
| 2026-10-24 | F0-02 | ✅ `godml.__version__` sale de `importlib.metadata` (fallback `0.0.0+unknown` sin instalar). `server.py` dejó de reportar `1.1.0` (FastAPI `version` y `service_version` = `__version__`); banners `v1.0.2` de `run_pipeline.py`, docstrings con versión y plantilla README (`v1.0.0` → `{godml_version}`) corregidos; README (`--source-tag`) y SECURITY.md sin versión del paquete. Test de guarda `tests/unit/test_version.py` (falla con literales) | Queda `v1.2.0/v1.3.0/v2.0.0` en el Roadmap del README: son metas, no la versión actual, y el roadmap está desactualizado (1.3.0 salió sin esos ítems) → F1-14 |
| 2026-10-24 | F0-01 (reaplicada) | ✅ Commit de licencia reaplicado sobre main + 2 headers nuevos de 1.3.0 (`observability.py`, `scaffold.py`) → 22 archivos con `SPDX-License-Identifier: MIT`. `CHANGELOG.md` creado con la nota de licencia | Historial: todos los autores humanos son el mantenedor (varias identidades) + dependabot; no se requiere consentimiento de terceros |
| 2026-10-24 | F0-09 | ✅ No requería merge: `chore/bump-version-1.2.2` ya estaba en main vía squash del PR #69 (`ae98b32`, tag v1.2.4; árbol idéntico a `8dcddbb`). main está en **1.3.0** (PR #75 observability), publicada en PyPI (última: 1.3.0) → la siguiente es 1.3.1, como dice el plan. Editable reinstalado: reporta 1.3.0 | **La línea base de F0-08 se había medido sobre la rama vieja (1.2.4).** Base nueva sobre main `57b0290`: 358 tests pasan; cobertura reportada 57.95 % (1750/3020), **real 48.22 %** (1978/4102); ruff 26; `BLE001` 95 / `S110` 12; ruff format 111 archivos; mypy 46 errores en 15 archivos; bandit 8 MEDIUM / 20 LOW. F0-01 se reaplica sobre main |
| 2026-10-24 | F0-08, F0-01 | ✅ Línea base: cobertura real 41.2 % (55.7 % reportado con `omit`). Licencia MIT restaurada (el texto Apache había vuelto por accidente en 8c1e8c4) | D2 revisada a 3.11+. Nuevas tareas F0-09…F0-12; README_TEMPLATE agregado a F1-14. Orden sugerido: F0-09 → F0-02 → F0-03 → F0-10 → F0-11 |
| 2026-10-24 | D2–D7 | Todas aprobadas según propuesta | Sin decisiones pendientes; arrancar F0 |
| 2026-10-24 | D1 | Licencia: MIT | F0-01 desbloqueada |
| 2026-10-24 | — | Plan creado | Pendiente confirmar decisiones D2–D7 |
