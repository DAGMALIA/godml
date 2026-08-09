# godml/monitoring_service/observability.py
# Copyright (c) 2025 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License
"""
Observabilidad de runtime para modelos servidos por GODML.

Este módulo cubre el hueco entre MLflow (observabilidad de *entrenamiento*) y
Prometheus/Grafana (observabilidad de *producción*). Expone tres cosas:

1. Métricas Prometheus del servicio de inferencia (latencia, throughput, errores).
2. Distribución de las predicciones que el modelo está emitiendo en vivo.
3. Drift de features vía PSI, calculado en proceso contra un baseline generado
   durante el entrenamiento. Solo el PSI resultante viaja a Prometheus: las
   features nunca se almacenan en la TSDB.

`prometheus_client` es una dependencia opcional (`pip install godml[observability]`).
Si no está instalada, todas las métricas se degradan a no-ops y el servicio sigue
funcionando igual.
"""

from __future__ import annotations

import json
import os
import threading
from collections import deque
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from godml.monitoring_service.logger import godml_logger

# ==========================================================
# 📦 DEPENDENCIA OPCIONAL
# ==========================================================
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        REGISTRY,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - depende del entorno
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"
    REGISTRY = None
    Counter = Gauge = Histogram = None

    def generate_latest(*_args, **_kwargs) -> bytes:
        return b""


class _NoopMetric:
    """Sustituto silencioso cuando prometheus_client no está disponible."""

    def labels(self, *_args, **_kwargs) -> "_NoopMetric":
        return self

    def inc(self, *_args, **_kwargs) -> None:
        return None

    def dec(self, *_args, **_kwargs) -> None:
        return None

    def set(self, *_args, **_kwargs) -> None:
        return None

    def observe(self, *_args, **_kwargs) -> None:
        return None


def _build(factory, name: str, doc: str, labelnames: Iterable[str] = (), **kwargs):
    """
    Crea una métrica tolerando reimportaciones del módulo.

    Con `uvicorn --reload` o bajo pytest el módulo puede evaluarse más de una vez
    en el mismo proceso; prometheus_client lanza ValueError al reregistrar un
    colector. En ese caso reutilizamos el que ya está en el registry.
    """
    if not PROMETHEUS_AVAILABLE:
        return _NoopMetric()
    try:
        return factory(name, doc, list(labelnames), **kwargs)
    except ValueError:
        existing = getattr(REGISTRY, "_names_to_collectors", {}).get(name)
        return existing if existing is not None else _NoopMetric()


# ==========================================================
# ⚙️ CONFIGURACIÓN
# ==========================================================
def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        godml_logger.warning(f"⚠️ {name} inválido, usando default {default}")
        return default


METRICS_ENABLED = _env_flag("GODML_METRICS_ENABLED", True) and PROMETHEUS_AVAILABLE
DRIFT_ENABLED = _env_flag("GODML_DRIFT_ENABLED", True)

# Umbrales estándar de la industria para PSI.
PSI_MODERATE_THRESHOLD = 0.10
PSI_SIGNIFICANT_THRESHOLD = 0.25

# Buckets pensados para inferencia: la mayoría de los modelos responden en
# milisegundos, y los defaults de prometheus_client pierden resolución ahí.
LATENCY_BUCKETS = (
    0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)

_MODEL_LABELS = ("model", "version", "environment")


# ==========================================================
# 📊 MÉTRICAS
# ==========================================================
predictions_total = _build(
    Counter,
    "godml_predictions_total",
    "Predicciones procesadas, desglosadas por resultado",
    (*_MODEL_LABELS, "status"),
)

prediction_latency_seconds = _build(
    Histogram,
    "godml_prediction_latency_seconds",
    "Latencia de inferencia extremo a extremo",
    _MODEL_LABELS,
    buckets=LATENCY_BUCKETS,
)

prediction_value = _build(
    Histogram,
    "godml_prediction_value",
    "Distribución de los valores predichos por el modelo",
    _MODEL_LABELS,
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

prediction_batch_size = _build(
    Histogram,
    "godml_prediction_batch_size",
    "Cantidad de filas por request de inferencia",
    _MODEL_LABELS,
    buckets=(1, 2, 5, 10, 25, 50, 100, 250, 500, 1000),
)

model_loaded = _build(
    Gauge,
    "godml_model_loaded",
    "1 si el modelo está cargado y listo para servir, 0 si no",
    _MODEL_LABELS,
)

http_requests_total = _build(
    Counter,
    "godml_http_requests_total",
    "Requests HTTP atendidos por el servicio de inferencia",
    ("method", "path", "status"),
)

http_request_duration_seconds = _build(
    Histogram,
    "godml_http_request_duration_seconds",
    "Duración de los requests HTTP",
    ("method", "path"),
    buckets=LATENCY_BUCKETS,
)

feature_drift_psi = _build(
    Gauge,
    "godml_feature_drift_psi",
    "PSI de cada feature contra el baseline de entrenamiento",
    ("model", "environment", "feature"),
)

drift_features_significant = _build(
    Gauge,
    "godml_drift_features_significant",
    f"Cantidad de features con PSI > {PSI_SIGNIFICANT_THRESHOLD}",
    ("model", "environment"),
)

drift_baseline_loaded = _build(
    Gauge,
    "godml_drift_baseline_loaded",
    "1 si hay baseline de drift cargado, 0 si no",
    ("model", "environment"),
)

drift_window_samples = _build(
    Gauge,
    "godml_drift_window_samples",
    "Muestras acumuladas en la ventana deslizante de drift",
    ("model", "environment"),
)


# ==========================================================
# 🧮 PSI
# ==========================================================
def compute_psi(expected: Iterable[float], actual: Iterable[float], epsilon: float = 1e-6) -> float:
    """
    Population Stability Index entre dos vectores de proporciones ya binneados.

    PSI = Σ (actual - expected) * ln(actual / expected)

    Ambos vectores se renormalizan y se recortan en `epsilon` para que un bin
    vacío no produzca infinito.
    """
    e = np.clip(np.asarray(list(expected), dtype=float), epsilon, None)
    a = np.clip(np.asarray(list(actual), dtype=float), epsilon, None)
    if e.size == 0 or e.size != a.size:
        raise ValueError("Los vectores de proporciones deben tener el mismo tamaño y no ser vacíos")
    e = e / e.sum()
    a = a / a.sum()
    return float(np.sum((a - e) * np.log(a / e)))


def psi_severity(psi: float) -> str:
    """Traduce un PSI al vocabulario habitual de model risk management."""
    if psi < PSI_MODERATE_THRESHOLD:
        return "stable"
    if psi < PSI_SIGNIFICANT_THRESHOLD:
        return "moderate"
    return "significant"


# ==========================================================
# 🧊 BASELINE
# ==========================================================
BASELINE_FILENAME = "drift_baseline.json"
_CATEGORICAL_OTHER = "__other__"


def build_baseline(
    X: pd.DataFrame,
    n_bins: int = 10,
    max_categories: int = 20,
    model_name: str = "unknown",
    model_version: str = "unknown",
) -> dict[str, Any]:
    """
    Resume la distribución de las features de entrenamiento.

    Guarda únicamente bordes de bins y proporciones — nunca filas del dataset —
    para que el artefacto sea seguro de distribuir junto al modelo aunque el
    training set contenga datos sensibles.
    """
    features: dict[str, Any] = {}

    for column in X.columns:
        series = X[column].dropna()
        if series.empty:
            continue

        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            quantiles = np.quantile(series.to_numpy(dtype=float), np.linspace(0, 1, n_bins + 1))
            # Features constantes o casi constantes colapsan los bordes; unique()
            # los deja consistentes y np.histogram sigue siendo válido.
            edges = np.unique(quantiles)
            if edges.size < 2:
                continue
            counts, _ = np.histogram(series.to_numpy(dtype=float), bins=edges)
            total = counts.sum()
            if total == 0:
                continue
            features[str(column)] = {
                "type": "numeric",
                # Los extremos se abren en el server para absorber valores fuera de rango.
                "edges": [float(e) for e in edges],
                "proportions": [float(c / total) for c in counts],
            }
        else:
            counts = series.astype(str).value_counts()
            top = counts.head(max_categories)
            proportions = {str(k): float(v / len(series)) for k, v in top.items()}
            remainder = float((len(series) - top.sum()) / len(series))
            if remainder > 0:
                proportions[_CATEGORICAL_OTHER] = remainder
            features[str(column)] = {"type": "categorical", "proportions": proportions}

    return {
        "schema_version": 1,
        "model": model_name,
        "version": model_version,
        "n_samples": int(len(X)),
        "features": features,
    }


def save_baseline(baseline: Mapping[str, Any], directory: str | Path) -> Path:
    """Escribe el baseline junto al modelo. Devuelve la ruta final."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / BASELINE_FILENAME
    path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return path


def load_baseline(path: str | Path) -> dict[str, Any] | None:
    """Lee un baseline desde disco. Devuelve None si no existe o está corrupto."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        godml_logger.warning(f"⚠️ Baseline de drift ilegible en {path}: {e}")
        return None
    if not isinstance(baseline, dict) or "features" not in baseline:
        godml_logger.warning(f"⚠️ Baseline de drift con formato inesperado en {path}")
        return None
    return baseline


def find_baseline(search_dirs: Iterable[str | Path]) -> Path | None:
    """Busca `drift_baseline.json` en los directorios dados, en orden."""
    override = os.getenv("GODML_BASELINE_PATH")
    if override:
        candidate = Path(override)
        if candidate.exists():
            return candidate
        godml_logger.warning(f"⚠️ GODML_BASELINE_PATH apunta a una ruta inexistente: {candidate}")

    for directory in search_dirs:
        candidate = Path(directory) / BASELINE_FILENAME
        if candidate.exists():
            return candidate
    return None


# ==========================================================
# 🌊 MONITOR DE DRIFT
# ==========================================================
class DriftMonitor:
    """
    Calcula PSI sobre una ventana deslizante de las features vistas en producción.

    El cálculo no ocurre por request: se acumulan observaciones y se recalcula
    cada `refresh_every` muestras, de modo que el costo por predicción sea un
    append a un deque acotado.
    """

    def __init__(
        self,
        baseline: Mapping[str, Any] | None,
        window: int | None = None,
        min_samples: int | None = None,
        refresh_every: int | None = None,
    ):
        self.baseline = baseline or {}
        self.features: dict[str, Any] = dict(self.baseline.get("features", {}))
        # El PSI está sesgado hacia arriba en muestras chicas: con 10 bins y solo
        # 100 observaciones de la MISMA distribución la mediana da ~0.09, al borde
        # del umbral "moderado" (0.10), y un 1% de las ventanas supera 0.25. Medido
        # sobre 200 ventanas por tamaño con una normal estándar:
        #     n=100 → mediana 0.089, p95 0.182, 1.0% de falsos positivos
        #     n=300 → mediana 0.030, p95 0.058, 0.0%
        #     n=500 → mediana 0.016, p95 0.035, 0.0%
        # De ahí el mínimo de 300: por debajo de eso el ruido del estimador se
        # confunde con drift real y el dashboard queda en ámbar permanente.
        self.window = window if window is not None else _env_int("GODML_DRIFT_WINDOW", 1000)
        self.min_samples = (
            min_samples if min_samples is not None else _env_int("GODML_DRIFT_MIN_SAMPLES", 300)
        )
        self.refresh_every = (
            refresh_every if refresh_every is not None else _env_int("GODML_DRIFT_REFRESH_EVERY", 100)
        )
        self._buffers: dict[str, deque] = {
            name: deque(maxlen=self.window) for name in self.features
        }
        self._since_refresh = 0
        self._lock = threading.Lock()
        self.last_psi: dict[str, float] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.features)

    @property
    def samples(self) -> int:
        if not self._buffers:
            return 0
        return max(len(buf) for buf in self._buffers.values())

    def observe(self, rows: pd.DataFrame) -> bool:
        """
        Acumula un batch de filas. Devuelve True si toca recalcular el PSI.
        """
        if not self.enabled:
            return False
        with self._lock:
            for name in self.features:
                if name not in rows.columns:
                    continue
                values = rows[name].dropna().tolist()
                if values:
                    self._buffers[name].extend(values)
            self._since_refresh += len(rows)
            if self._since_refresh >= self.refresh_every and self.samples >= self.min_samples:
                self._since_refresh = 0
                return True
            return False

    def compute(self) -> dict[str, float]:
        """Recalcula el PSI de cada feature contra el baseline."""
        with self._lock:
            snapshot = {name: list(buf) for name, buf in self._buffers.items()}

        results: dict[str, float] = {}
        for name, values in snapshot.items():
            if len(values) < self.min_samples:
                continue
            spec = self.features[name]
            try:
                if spec["type"] == "numeric":
                    results[name] = self._psi_numeric(spec, values)
                else:
                    results[name] = self._psi_categorical(spec, values)
            except (ValueError, TypeError, KeyError) as e:
                godml_logger.warning(f"⚠️ No se pudo calcular PSI de '{name}': {e}")

        self.last_psi = results
        return results

    @staticmethod
    def _psi_numeric(spec: Mapping[str, Any], values: list) -> float:
        edges = np.asarray(spec["edges"], dtype=float)
        # Abrimos los extremos para que los valores fuera del rango de training
        # caigan en el primer/último bin en lugar de descartarse: un shift hacia
        # afuera del rango es justamente la señal de drift que interesa.
        open_edges = np.concatenate(([-np.inf], edges[1:-1], [np.inf]))
        numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna().to_numpy(dtype=float)
        if numeric.size == 0:
            raise ValueError("sin valores numéricos válidos en la ventana")
        counts, _ = np.histogram(numeric, bins=open_edges)
        return compute_psi(spec["proportions"], counts / counts.sum())

    @staticmethod
    def _psi_categorical(spec: Mapping[str, Any], values: list) -> float:
        expected: dict[str, float] = dict(spec["proportions"])
        known = set(expected) - {_CATEGORICAL_OTHER}
        observed = pd.Series([str(v) for v in values]).value_counts(normalize=True)

        # Las categorías nuevas se agregan en __other__, que siempre existe en el
        # vector observado aunque el baseline no lo tuviera.
        actual = {category: float(observed.get(category, 0.0)) for category in known}
        actual[_CATEGORICAL_OTHER] = float(
            sum(v for k, v in observed.items() if k not in known)
        )
        expected.setdefault(_CATEGORICAL_OTHER, 0.0)

        keys = sorted(expected)
        return compute_psi([expected[k] for k in keys], [actual.get(k, 0.0) for k in keys])


# ==========================================================
# 🎛️ FACHADA PARA EL SERVICIO
# ==========================================================
class ModelObserver:
    """
    Punto único de instrumentación para un servicio de inferencia GODML.

    Encapsula labels, métricas y drift para que `server.py` no tenga que saber
    nada de Prometheus.
    """

    def __init__(
        self,
        model_name: str | None = None,
        model_version: str | None = None,
        environment: str | None = None,
        baseline_path: str | Path | None = None,
    ):
        self.model_name = model_name or os.getenv("GODML_MODEL_NAME", "unknown")
        self.model_version = model_version or os.getenv("GODML_MODEL_VERSION", "unknown")
        self.environment = environment or os.getenv("GODML_ENV", "dev").lower()
        self._labels = (self.model_name, self.model_version, self.environment)
        self._drift_labels = (self.model_name, self.environment)

        baseline = load_baseline(baseline_path) if baseline_path else None
        self.drift = DriftMonitor(baseline if DRIFT_ENABLED else None)
        drift_baseline_loaded.labels(*self._drift_labels).set(1 if self.drift.enabled else 0)
        if self.drift.enabled:
            godml_logger.info(
                f"🌊 Drift activo sobre {len(self.drift.features)} features "
                f"(ventana={self.drift.window}, mínimo={self.drift.min_samples})"
            )

    # ── estado del modelo ───────────────────────────────
    def set_model_loaded(self, loaded: bool) -> None:
        model_loaded.labels(*self._labels).set(1 if loaded else 0)

    # ── inferencia ──────────────────────────────────────
    def record_prediction(
        self,
        latency: float,
        status: str = "success",
        predictions: Iterable[float] | None = None,
        features: pd.DataFrame | None = None,
    ) -> None:
        predictions_total.labels(*self._labels, status).inc()
        prediction_latency_seconds.labels(*self._labels).observe(latency)

        if predictions is not None:
            values = list(predictions)
            prediction_batch_size.labels(*self._labels).observe(len(values))
            for value in values:
                try:
                    prediction_value.labels(*self._labels).observe(float(value))
                except (TypeError, ValueError):
                    # Predicciones no escalares (multiclase, texto) no alimentan
                    # el histograma, pero el resto de las métricas sigue viva.
                    break

        if features is not None and self.drift.enabled:
            self._observe_drift(features)

    def _observe_drift(self, features: pd.DataFrame) -> None:
        should_refresh = self.drift.observe(features)
        drift_window_samples.labels(*self._drift_labels).set(self.drift.samples)
        if not should_refresh:
            return
        psi_by_feature = self.drift.compute()
        significant = 0
        for feature, psi in psi_by_feature.items():
            feature_drift_psi.labels(self.model_name, self.environment, feature).set(psi)
            if psi >= PSI_SIGNIFICANT_THRESHOLD:
                significant += 1
                godml_logger.warning(f"🚨 Drift significativo en '{feature}': PSI={psi:.4f}")
        drift_features_significant.labels(*self._drift_labels).set(significant)

    # ── HTTP ────────────────────────────────────────────
    def record_http(self, method: str, path: str, status: int, duration: float) -> None:
        http_requests_total.labels(method, path, str(status)).inc()
        http_request_duration_seconds.labels(method, path).observe(duration)

    # ── exposición ──────────────────────────────────────
    def snapshot(self) -> dict[str, Any]:
        """Vista JSON del estado de drift, para inspección sin Prometheus."""
        return {
            "model": self.model_name,
            "version": self.model_version,
            "environment": self.environment,
            "prometheus_enabled": METRICS_ENABLED,
            "drift": {
                "enabled": self.drift.enabled,
                "features_tracked": len(self.drift.features),
                "window_samples": self.drift.samples,
                "min_samples": self.drift.min_samples,
                "psi": {
                    feature: {"value": round(psi, 6), "severity": psi_severity(psi)}
                    for feature, psi in self.drift.last_psi.items()
                },
            },
        }


def render_metrics() -> tuple[bytes, str]:
    """Payload de `/metrics` en formato de exposición Prometheus."""
    if not METRICS_ENABLED:
        return (
            b"# godml: prometheus_client no instalado o metricas deshabilitadas\n",
            CONTENT_TYPE_LATEST,
        )
    return generate_latest(), CONTENT_TYPE_LATEST
