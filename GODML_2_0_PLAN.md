# GoDML 2.0 — Plan maestro

> **GoDML** — Governed · Observable · Declarative Machine Learning
> Del YAML a producción: **entrenar → gobernar → servir → observar**, con herramientas de productividad alrededor.

Este documento es la fuente de verdad del proyecto 2.0. Claude Code lo lee al iniciar cada sesión y **actualiza los estados** al terminar cada tarea (ver `CLAUDE.md`).

**Leyenda de estado:** ⬜ pendiente · 🟨 en progreso · ✅ hecho · ⛔ bloqueado · ⏭️ descartado

---

## 0. Tablero de estado

| Fase | Nombre | Versión objetivo | Estado |
|---|---|---|---|
| F0 | Fundaciones del repo | 1.3.1 | 🟨 |
| F1 | Hotfixes críticos 1.x (protege usuarios actuales) | 1.3.1 | ⬜ |
| F2 | Arquitectura 2.0: core, spec v2, plugins | 2.0.0a1 | ⬜ |
| F3 | Pilar **Govern** | 2.0.0a1 | ⬜ |
| F4 | Pilar **Train** | 2.0.0a2 | ⬜ |
| F5 | Pilar **Serve** | 2.0.0b1 | ⬜ |
| F6 | Pilar **Observe** | 2.0.0b1 | ⬜ |
| F7 | Pilar **Tools** | 2.0.0b2 | ⬜ |
| F8 | Empaquetado: PyPI por pilar + conda-forge | 2.0.0rc1 | ⬜ |
| F9 | Docs, ejemplos, migración y lanzamiento | 2.0.0 | ⬜ |

**Fase activa:** F0

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
| D8 | Resuelta por el usuario (texto de la versión nueva del plan no recibido en sesión; reemplazar esta fila al pegarlo) | ✅ 2026-10-24 |
| D9 | F0-04: el formateo masivo (`ruff format`) va en un **commit aislado primero**, registrado en `.git-blame-ignore-revs` | ✅ 2026-10-24 |

---

## 4. Fases y tareas

Formato: **ID** · estado · descripción → *criterio de aceptación*

### F0 — Fundaciones del repo (1.3.1)

- **F0-01** ✅ Licencia MIT (D1): reemplazar el texto de `LICENSE` por MIT estándar con línea de copyright del autor; usar `license = "MIT"` (SPDX) en `pyproject.toml`; verificar classifiers, headers y README; revisar en el historial si hubo contribuciones externas (si las hay, pedir consentimiento para el cambio de texto) y nota en CHANGELOG aclarando que el proyecto siempre se distribuyó como MIT → *`MIT` es el único identificador de licencia en todo el repo*
- **F0-02** ✅ Fuente única de versión (D6); eliminar versiones hardcodeadas en banners, plantillas, `service_version` y SECURITY.md → *`grep` de versiones literales sin resultados fuera de pyproject*
- **F0-03** ✅ Eliminar `godml.egg-info/` del repo y verificar `.gitignore`
- **F0-04** ✅ Tooling: ruff (lint + format), mypy (modo gradual), pre-commit; regla que prohíba `except Exception: pass` (ruff `S110`, `BLE001`) → *CI falla con violaciones*
- **F0-05** ⬜ CI que realmente bloquea: quitar `|| true` de bandit y pip-audit; matriz de Python según D2
- **F0-06** ⬜ Eliminar workflow suelto `godml/deploy_service/.github/workflows/docker-ci.yml` (acciones sin pinear)
- **F0-07** ⬜ Alinear SECURITY.md con la realidad: IDs de Safety ignorados, lockfile, SBOM, fecha de revisión
- **F0-08** ✅ Correr suite actual y registrar línea base (tests pasando, cobertura) en el log de estado
- **F0-09** ✅ **(hacer primero)** Integrar a `main` la rama `chore/bump-version-1.2.2` (fix de `skops_trusted_types` para XGBoost + bump); verificar la última versión publicada en PyPI para numerar correctamente 1.3.1 → *main contiene ambos commits, instalación editable reporta la versión correcta*
- **F0-10** ✅ Cobertura real: eliminar la lista `omit` de `[tool.coverage.run]` (salvo tests y código generado); `fail_under` se fija a la cobertura real actual (~41 %) y sube por fase → *el reporte de CI coincide con la cobertura sin exclusiones*
- **F0-11** ✅ Quitar `-p no:warnings` de `addopts`; usar `filterwarnings` explícitos y tratar como error los `DeprecationWarning` emitidos por `godml` → *los warnings de terceros siguen visibles; los propios fallan el test*
- **F0-12** ⬜ `LICENSE_REPORT.md` generado automáticamente (pip-licenses) en CI en lugar de mantenerse a mano
- **F0-13** ⬜ *(descripción pendiente: definida en una versión del plan que no llegó a la sesión)*
- **F0-14** ✅ `.mailmap` que unifica las identidades del mantenedor en `Arturo Gutiérrez Rubio Rojas <agtzrubio@dagmalia.com>`, sin reescribir historial → *`git shortlog -sne` muestra una sola identidad humana*

### F1 — Hotfixes críticos 1.x (1.3.1)

Cada fix lleva primero un test que reproduce el bug.

- **F1-01** ⬜ Compliance fail-closed: `ComplianceEngine.apply`, `run_pipeline_preprocessing` y `MLflowExecutor.run` dejan de devolver el df original ante error → *test: excepción en compliance aborta el pipeline*
- **F1-02** ⬜ No subir el dataset crudo a MLflow; registrar solo hash y esquema (o el dataset ya cumplido si se pide explícitamente) → *test: el artefacto de MLflow no contiene columnas PII*
- **F1-03** ⬜ Quitar `except Exception: pass` en `MLflowExecutor.validate`; los `ValidationError` críticos se propagan
- **F1-04** ⬜ SageMaker `preprocess.py`: corregir `ComplianceRegistry.get` → `get_compliance` y la firma de `apply`; fallar si compliance no puede aplicarse
- **F1-05** ⬜ Verificar `dataset.hash` en `godml run` cuando está fijado; error si no coincide
- **F1-06** ⬜ Hash de PII con HMAC-SHA256 y llave desde `GODML_PII_KEY` (error en prod si falta)
- **F1-07** ⬜ Detector de PII: heurística por nombre a nivel token (no substring), excluir la columna target, endurecer patrones de contenido (cvv, zip, coordenadas) → *tests con columnas `zip_code`, `hotel_id`, `plate`, `year`, `fare`*
- **F1-08** ⬜ Deploy: mapeo de puertos `{port}:8000` o CMD que lea `$PORT`; `serve` sin `reload` fuera de dev
- **F1-09** ⬜ `resolver.py`: recursión en listas de dicts e interpolación parcial (`"prefix-${X}"`)
- **F1-10** ⬜ Umbrales con dirección: métricas tipo pérdida (`mse`, `rmse`, `mae`, `log_loss`) se evalúan con `<=`
- **F1-11** ⬜ Server: reordenar features por `feature_names_in_` / `feature_names`; devolver `predict_proba` cuando exista
- **F1-12** ⬜ `import godml` sin efectos colaterales: quitar filtros globales de warnings, creación de `logs/` al importar y `logging.basicConfig`
- **F1-13** ⬜ Corregir `_is_safe_absolute_path` y `validate_model_path` con `Path.is_relative_to`
- **F1-14** ⬜ README honesto: quitar GDPR/HIPAA/SOX, corregir ejemplos de notebook/advisor/tune, agregar `target` al quick start y a `godml init`; corregir `godml/utils/README_TEMPLATE.txt` (no imponer badge MIT a proyectos de usuarios, Python 3.11+)
- **F1-15** ⬜ Publicar 1.3.1 con CHANGELOG

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

### F3 — Pilar Govern (2.0.0a1)

- **F3-01** ⬜ Motor de políticas con gates `pre-train`, `post-train`, `pre-deploy`; resultado estructurado (pass/fail/waived + razón)
- **F3-02** ⬜ Política PCI-DSS migrada al motor; arquitectura lista para nuevas políticas (sin anunciar GDPR/HIPAA hasta implementarlas)
- **F3-03** ⬜ Verificación de datos: sha256, esquema esperado y conteo mínimo de filas
- **F3-04** ⬜ Reglas por entorno: en `prod`, hash fijo, owner y aprobación obligatorios
- **F3-05** ⬜ `godml validate <dir>` sobre repo central completo, con salida para CI (JUnit/SARIF)
- **F3-06** ⬜ Reporte de gobernanza por run (JSON + Markdown) adjunto al bundle

### F4 — Pilar Train (2.0.0a2)

- **F4-01** ⬜ Estimador por import path (`xgboost.XGBClassifier`) además de alias de catálogo
- **F4-02** ⬜ Preprocesamiento como `sklearn.Pipeline` persistido junto con el modelo (elimina training-serving skew)
- **F4-03** ⬜ Corrección de multiclase y regresión en catálogo (XGBoost, RandomForest, Logistic)
- **F4-04** ⬜ `params` libres validados contra la firma del estimador (no se pierden en silencio)
- **F4-05** ⬜ Bring-your-own-model: registrar un `.pkl` existente con su pre/post bajo el mismo contrato
- **F4-06** ⬜ Executor local (sin MLflow) y executor MLflow como plugins
- **F4-07** ⬜ Executor SageMaker: imagen con godml instalado, hiperparámetros desconocidos rechazados en validación
- **F4-08** ⬜ Reintentos reales (solo errores transitorios) o eliminar `max_attempts`
- **F4-09** ⬜ LSTM movido a `train-dl`; eliminar `run_pipeline.py` muerto
- **F4-10** ⬜ Compatibilidad con scikit-learn 1.8 (`multi_class` retirado)

### F5 — Pilar Serve (2.0.0b1)

- **F5-01** ⬜ Formato de bundle: `manifest.json` (hashes, versión, firma de entrada/salida), modelo, pipeline, pre/post, baseline, reporte de gobernanza
- **F5-02** ⬜ `godml bundle build|inspect|verify`
- **F5-03** ⬜ Runtime único (reemplaza los 3 servidores actuales); lifespan en lugar de `on_event`
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

- **F8-01** ⬜ Extras por pilar en `pyproject.toml` (§2.2) con rangos de versión probados
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
| 1 | Al cerrar F1 | "GoDML 1.3.1: más seguro, fail-closed" + anuncio del camino a 2.0 |
| 2 | Al cerrar F2 | Los 5 pilares y la instalación por pilar |
| 3–7 | Al cerrar cada pilar | Un post por pilar con caso de uso y snippet |
| 8 | F9 | Lanzamiento 2.0 + conda-forge + historia del repo central de 500+ modelos |

---

## 7. Log de estado

Claude Code agrega una entrada por sesión (la más reciente arriba).

| Fecha | Tareas | Resultado | Notas / bloqueos |
|---|---|---|---|
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
