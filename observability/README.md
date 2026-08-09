# 👁️ Observabilidad de runtime — GODML

MLflow responde *cómo entrenó* el modelo. Este stack responde *cómo se está portando en producción*: latencia, throughput, errores y drift de features.

Todo es open source y self-hosted: Prometheus para las series temporales, Grafana para los tableros. Sin vendor lock-in y sin agentes propietarios.

---

## 🚀 Puesta en marcha

```bash
# 1. Instalar la extra de observabilidad
pip install "godml[observability]"

# 2. Levantar el modelo (expone /metrics automáticamente)
godml serve --environment dev

# 3. Levantar Prometheus + Grafana
docker compose -f observability/docker-compose.yml up -d
```

> ⚠️ **`godml-frontend` ya ocupa el puerto 3000.** Si lo tenés levantado, Grafana no
> puede arrancar. Movelo:
> ```bash
> GRAFANA_PORT=3001 docker compose -f observability/docker-compose.yml up -d
> ```

| Servicio | URL | Credenciales |
|---|---|---|
| Grafana | http://localhost:3000 (`GRAFANA_PORT`) | `admin` / `admin` (`GRAFANA_USER` / `GRAFANA_PASSWORD`) |
| Prometheus | http://localhost:9090 (`PROMETHEUS_PORT`) | — |
| Métricas del modelo | http://localhost:8000/metrics | — |
| Drift en JSON | http://localhost:8000/drift | — |

El dashboard **GODML — Model Serving** queda provisionado solo, en la carpeta `GODML`.

Por defecto Prometheus solo scrapea `dev`. Los targets de `qa` y `prod` están
comentados en [`prometheus/prometheus.yml`](prometheus/prometheus.yml): declarar un
target que no está corriendo deja `GodmlServiceDown` encendida para siempre, que es
justo el ruido que hace que la gente deje de mirar las alertas. Descomentalos cuando
esos ambientes existan de verdad.

Verificación rápida sin Grafana:

```bash
curl -s localhost:8000/metrics | grep godml_
curl -s localhost:8000/drift | jq
```

---

## 📊 Métricas expuestas

| Métrica | Tipo | Labels | Para qué sirve |
|---|---|---|---|
| `godml_predictions_total` | Counter | model, version, environment, status | Throughput y tasa de error |
| `godml_prediction_latency_seconds` | Histogram | model, version, environment | Percentiles p50/p95/p99 |
| `godml_prediction_value` | Histogram | model, version, environment | Distribución de los scores emitidos |
| `godml_prediction_batch_size` | Histogram | model, version, environment | Tamaño de los batches recibidos |
| `godml_model_loaded` | Gauge | model, version, environment | 1 = modelo en memoria |
| `godml_http_requests_total` | Counter | method, path, status | Tráfico por endpoint |
| `godml_http_request_duration_seconds` | Histogram | method, path | Latencia HTTP |
| `godml_feature_drift_psi` | Gauge | model, environment, feature | PSI por feature |
| `godml_drift_features_significant` | Gauge | model, environment | Cuántas features pasaron 0.25 |
| `godml_drift_baseline_loaded` | Gauge | model, environment | 1 = hay baseline cargado |
| `godml_drift_window_samples` | Gauge | model, environment | Muestras en la ventana deslizante |

`status` distingue `success`, `client_error` (4xx) y `error` (5xx). La separación importa: un payload mal formado por parte del cliente no debe leerse como una falla del modelo, y las alertas solo miran `error`.

---

## 🌊 Cómo funciona el drift

Prometheus es una base de series temporales agregadas, no un almacén de eventos: no sirve para guardar features fila por fila. Por eso el cálculo ocurre **en el proceso del modelo** y a Prometheus solo viaja el resultado.

```
godml run  ─┬─→ modelo .pkl
            └─→ drift_baseline.json   (bordes de bins + proporciones de X_train)
                        │
                        ▼
godml serve ──→ ventana deslizante de features en vivo
                        │
                        ▼
                  PSI por feature ──→ /metrics ──→ Prometheus ──→ Grafana
```

El baseline **no contiene filas del dataset**, solo bordes de bins y proporciones. Es seguro distribuirlo junto al modelo aunque el training set tenga datos sensibles.

### Interpretación del PSI

| PSI | Lectura |
|---|---|
| < 0.10 | Estable |
| 0.10 – 0.25 | Cambio moderado, vale la pena mirarlo |
| > 0.25 | Cambio significativo, evaluar reentrenamiento |

### Por qué la ventana mínima es 300

El PSI está sesgado hacia arriba en muestras chicas. Midiendo sobre 200 ventanas por tamaño con datos de la **misma** distribución (sin drift real):

| Ventana | PSI mediano | PSI p95 | % de ventanas > 0.25 |
|---|---|---|---|
| 100 | 0.089 | 0.182 | 1.0 % |
| 300 | 0.030 | 0.058 | 0.0 % |
| 500 | 0.016 | 0.035 | 0.0 % |
| 1000 | 0.011 | 0.018 | 0.0 % |

Con 100 muestras la mediana queda pegada al umbral de "moderado" y el tablero se pondría en ámbar sin que nada haya cambiado. De ahí que el mínimo por defecto sea 300 y la ventana 1000. Bajarlos hace el drift más reactivo pero mucho más ruidoso.

---

## ⚙️ Configuración

Todo se controla por variables de entorno, sin tocar código:

| Variable | Default | Qué hace |
|---|---|---|
| `GODML_METRICS_ENABLED` | `true` | Apaga la exposición Prometheus |
| `GODML_DRIFT_ENABLED` | `true` | Apaga el cálculo de drift |
| `GODML_DRIFT_WINDOW` | `1000` | Tamaño de la ventana deslizante |
| `GODML_DRIFT_MIN_SAMPLES` | `300` | Mínimo para calcular PSI |
| `GODML_DRIFT_REFRESH_EVERY` | `100` | Cada cuántas predicciones se recalcula |
| `GODML_BASELINE_PATH` | — | Ruta explícita al baseline |
| `GODML_MODEL_NAME` | `unknown` | Label `model` de las métricas |
| `GODML_MODEL_VERSION` | `unknown` | Label `version` de las métricas |

El PSI no se recalcula en cada request: se acumula en un deque acotado y se recomputa cada `GODML_DRIFT_REFRESH_EVERY` predicciones. El costo por predicción es un append.

---

## 🚨 Alertas incluidas

Definidas en [`prometheus/alerts.yml`](prometheus/alerts.yml):

| Alerta | Condición | Severidad |
|---|---|---|
| `GodmlServiceDown` | `/metrics` inalcanzable 2 min | critical |
| `GodmlModelNotLoaded` | `godml_model_loaded == 0` por 2 min | critical |
| `GodmlHighErrorRate` | > 5 % de 5xx durante 5 min | warning |
| `GodmlHighLatency` | p95 > 1 s durante 5 min | warning |
| `GodmlFeatureDriftSignificant` | PSI > 0.25 durante 15 min | warning |
| `GodmlManyFeaturesDrifting` | ≥ 3 features con drift a la vez | critical |

Prometheus las evalúa, pero **no las envía a ningún lado**: para notificaciones hay que sumar Alertmanager al compose y apuntarle un receptor (Slack, PagerDuty, email).

---

## 📈 Consultas útiles

```promql
# Throughput
sum(rate(godml_predictions_total[5m]))

# Tasa de error del modelo (solo 5xx)
sum(rate(godml_predictions_total{status="error"}[5m]))
  / sum(rate(godml_predictions_total[5m]))

# Latencia p95
histogram_quantile(0.95,
  sum by (le) (rate(godml_prediction_latency_seconds_bucket[5m])))

# Las 5 features con más drift
topk(5, godml_feature_drift_psi)

# Score promedio predicho — un corrimiento suele preceder al drift de features
sum(rate(godml_prediction_value_sum[10m]))
  / sum(rate(godml_prediction_value_count[10m]))
```

---

## 🧩 Qué cubre y qué no

| Necesidad | Cubierto por |
|---|---|
| Latencia, throughput, errores | ✅ Prometheus |
| Distribución de predicciones | ✅ Prometheus (histogram) |
| Drift de features | ✅ PSI en proceso → Prometheus |
| Métricas de entrenamiento | ✅ MLflow (ya integrado, no se duplica acá) |
| Traza por predicción individual | ❌ Requiere logs estructurados → Loki/Elastic |
| Ground truth y métricas de negocio | ❌ Llegan con retraso; requieren un job batch aparte |

Las dos últimas filas son limitaciones **de diseño**, no pendientes: Prometheus no es un almacén de eventos, y meterle cardinalidad por predicción lo rompe.

---

## 🐳 Notas de despliegue

- El compose scrapea `host.docker.internal`, que funciona en macOS, Windows y —vía `extra_hosts`— en Linux. Si el modelo corre como contenedor, reemplazar los targets por el nombre del servicio en la red de Docker.
- Prometheus retiene 30 días. Ajustable en `--storage.tsdb.retention.time`.
- Las credenciales de Grafana del compose son para desarrollo local. Antes de exponer el puerto en cualquier entorno compartido, reemplazarlas por secretos reales.
- El scrape de `/metrics` no se contabiliza a sí mismo en `godml_http_requests_total`: inflaría el RPS con tráfico interno.
