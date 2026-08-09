# test_observability.py
import numpy as np
import pandas as pd
import pytest

from godml.monitoring_service.observability import (
    BASELINE_FILENAME,
    METRICS_ENABLED,
    DriftMonitor,
    ModelObserver,
    PSI_SIGNIFICANT_THRESHOLD,
    build_baseline,
    compute_psi,
    find_baseline,
    load_baseline,
    psi_severity,
    render_metrics,
    save_baseline,
)

# El PSI y el baseline no dependen de prometheus_client, pero la exposición sí.
# Sin la extra instalada las métricas son no-ops y una aserción sobre el payload
# no verificaría nada: mejor saltear explícitamente que pasar en falso.
requiere_prometheus = pytest.mark.skipif(
    not METRICS_ENABLED,
    reason="requiere la extra observability (pip install godml[observability])",
)


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def training_data(rng):
    return pd.DataFrame({
        "edad": rng.normal(40, 10, 5000),
        "ingreso": rng.lognormal(10, 0.5, 5000),
        "pais": rng.choice(["AR", "MX", "CO"], 5000, p=[0.6, 0.3, 0.1]),
    })


@pytest.fixture
def baseline(training_data):
    return build_baseline(training_data, model_name="test-model", model_version="1.0")


class TestComputePSI:

    def test_distribuciones_identicas_dan_cero(self):
        assert compute_psi([0.25] * 4, [0.25] * 4) == pytest.approx(0.0, abs=1e-9)

    def test_psi_es_simetrico_en_magnitud(self):
        a, b = [0.5, 0.3, 0.2], [0.2, 0.3, 0.5]
        assert compute_psi(a, b) == pytest.approx(compute_psi(b, a), rel=1e-6)

    def test_bin_vacio_no_produce_infinito(self):
        """El clipping en epsilon evita el log(0) cuando un bin queda sin datos."""
        psi = compute_psi([0.5, 0.5], [1.0, 0.0])
        assert np.isfinite(psi) and psi > 0

    def test_vectores_de_distinto_largo_fallan(self):
        with pytest.raises(ValueError):
            compute_psi([0.5, 0.5], [0.3, 0.3, 0.4])

    def test_severidad_por_umbral(self):
        assert psi_severity(0.05) == "stable"
        assert psi_severity(0.15) == "moderate"
        assert psi_severity(0.40) == "significant"


class TestBuildBaseline:

    def test_captura_numericas_y_categoricas(self, baseline):
        assert baseline["features"]["edad"]["type"] == "numeric"
        assert baseline["features"]["pais"]["type"] == "categorical"
        assert baseline["n_samples"] == 5000

    def test_las_proporciones_suman_uno(self, baseline):
        for name, spec in baseline["features"].items():
            values = (
                spec["proportions"]
                if spec["type"] == "numeric"
                else list(spec["proportions"].values())
            )
            assert sum(values) == pytest.approx(1.0, abs=1e-6), name

    def test_no_persiste_filas_del_dataset(self, baseline):
        """El baseline debe ser distribucional: nunca datos crudos."""
        spec = baseline["features"]["edad"]
        assert set(spec) == {"type", "edges", "proportions"}
        # 10 bins => 11 bordes como máximo
        assert len(spec["edges"]) <= 11

    def test_feature_constante_se_descarta(self):
        """Una columna sin varianza colapsa los bordes y no aporta señal."""
        df = pd.DataFrame({"constante": [7.0] * 100, "variable": np.arange(100.0)})
        features = build_baseline(df)["features"]
        assert "constante" not in features
        assert "variable" in features

    def test_categorias_raras_se_agrupan(self, rng):
        df = pd.DataFrame({"cat": [f"c{i}" for i in range(200)]})
        spec = build_baseline(df, max_categories=5)["features"]["cat"]
        assert len(spec["proportions"]) == 6  # 5 + __other__
        assert "__other__" in spec["proportions"]


class TestBaselinePersistence:

    def test_roundtrip(self, baseline, tmp_path):
        path = save_baseline(baseline, tmp_path)
        assert path.name == BASELINE_FILENAME
        assert load_baseline(path)["features"].keys() == baseline["features"].keys()

    def test_archivo_inexistente_devuelve_none(self, tmp_path):
        assert load_baseline(tmp_path / "no-existe.json") is None

    def test_json_corrupto_devuelve_none_sin_explotar(self, tmp_path):
        corrupto = tmp_path / BASELINE_FILENAME
        corrupto.write_text("{esto no es json", encoding="utf-8")
        assert load_baseline(corrupto) is None

    def test_find_baseline_respeta_el_orden(self, baseline, tmp_path):
        segundo = tmp_path / "segundo"
        segundo.mkdir()
        save_baseline(baseline, segundo)
        assert find_baseline([tmp_path / "vacio", segundo]) == segundo / BASELINE_FILENAME

    def test_find_baseline_sin_resultados(self, tmp_path):
        assert find_baseline([tmp_path]) is None


class TestDriftMonitor:

    def _monitor(self, baseline, n):
        return DriftMonitor(baseline, window=n, min_samples=n, refresh_every=n)

    def test_misma_distribucion_es_estable(self, baseline, rng):
        mon = self._monitor(baseline, 2000)
        mon.observe(pd.DataFrame({
            "edad": rng.normal(40, 10, 2000),
            "ingreso": rng.lognormal(10, 0.5, 2000),
            "pais": rng.choice(["AR", "MX", "CO"], 2000, p=[0.6, 0.3, 0.1]),
        }))
        for feature, psi in mon.compute().items():
            assert psi < 0.1, f"{feature} deberia ser estable, dio {psi}"

    def test_shift_de_media_se_detecta(self, baseline, rng):
        mon = self._monitor(baseline, 2000)
        mon.observe(pd.DataFrame({
            "edad": rng.normal(65, 10, 2000),          # +25 años
            "ingreso": rng.lognormal(10, 0.5, 2000),   # sin cambio
            "pais": rng.choice(["AR", "MX", "CO"], 2000, p=[0.6, 0.3, 0.1]),
        }))
        psi = mon.compute()
        assert psi["edad"] > PSI_SIGNIFICANT_THRESHOLD
        # Una feature que no cambió no debe contagiarse del drift de otra.
        assert psi["ingreso"] < 0.1

    def test_categoria_nueva_se_detecta(self, baseline, rng):
        mon = self._monitor(baseline, 2000)
        mon.observe(pd.DataFrame({
            "edad": rng.normal(40, 10, 2000),
            "ingreso": rng.lognormal(10, 0.5, 2000),
            "pais": rng.choice(["AR", "BR"], 2000, p=[0.3, 0.7]),  # BR no está en el baseline
        }))
        assert mon.compute()["pais"] > PSI_SIGNIFICANT_THRESHOLD

    def test_valores_fuera_del_rango_de_training(self, baseline, rng):
        """Los extremos se abren: un shift fuera del rango es señal, no descarte."""
        mon = self._monitor(baseline, 1000)
        mon.observe(pd.DataFrame({"edad": rng.normal(500, 5, 1000)}))
        assert mon.compute()["edad"] > PSI_SIGNIFICANT_THRESHOLD

    def test_no_calcula_por_debajo_del_minimo(self, baseline, rng):
        mon = DriftMonitor(baseline, window=1000, min_samples=500, refresh_every=10)
        mon.observe(pd.DataFrame({"edad": rng.normal(40, 10, 50)}))
        assert mon.compute() == {}

    def test_la_ventana_es_deslizante(self, baseline, rng):
        mon = DriftMonitor(baseline, window=100, min_samples=10, refresh_every=10)
        mon.observe(pd.DataFrame({"edad": rng.normal(40, 10, 500)}))
        assert mon.samples == 100

    def test_refresco_solo_al_alcanzar_el_umbral(self, baseline, rng):
        mon = DriftMonitor(baseline, window=1000, min_samples=100, refresh_every=100)
        assert mon.observe(pd.DataFrame({"edad": rng.normal(40, 10, 50)})) is False
        assert mon.observe(pd.DataFrame({"edad": rng.normal(40, 10, 60)})) is True

    def test_columnas_ausentes_no_rompen(self, baseline, rng):
        mon = self._monitor(baseline, 500)
        mon.observe(pd.DataFrame({"edad": rng.normal(40, 10, 500)}))
        psi = mon.compute()
        assert "edad" in psi and "pais" not in psi

    def test_sin_baseline_queda_deshabilitado(self):
        mon = DriftMonitor(None)
        assert mon.enabled is False
        assert mon.observe(pd.DataFrame({"x": [1, 2, 3]})) is False


class TestModelObserver:

    @requiere_prometheus
    def test_expone_metricas_en_el_formato_prometheus(self, baseline, tmp_path):
        path = save_baseline(baseline, tmp_path)
        obs = ModelObserver(
            model_name="test-model", model_version="1.0",
            environment="dev", baseline_path=path,
        )
        obs.set_model_loaded(True)
        obs.record_prediction(0.01, "success", predictions=[0.7])
        obs.record_http("POST", "/predict", 200, 0.01)

        body = render_metrics()[0].decode()
        for metric in (
            "godml_predictions_total",
            "godml_prediction_latency_seconds_bucket",
            "godml_prediction_value_bucket",
            "godml_model_loaded",
            "godml_http_requests_total",
        ):
            assert metric in body

    def test_predicciones_no_escalares_no_rompen(self, tmp_path):
        """Multiclase devuelve listas: el histograma se saltea, el resto sigue."""
        obs = ModelObserver(model_name="multiclase", environment="dev")
        obs.record_prediction(0.01, "success", predictions=[[0.1, 0.9], [0.4, 0.6]])

    def test_snapshot_sin_baseline(self):
        snap = ModelObserver(model_name="sin-baseline", environment="dev").snapshot()
        assert snap["drift"]["enabled"] is False
        assert snap["drift"]["psi"] == {}


class TestVersionEndpoint:

    def test_reporta_la_version_real_y_no_la_cadena_dev(self, monkeypatch):
        """
        El default era literalmente "dev", así que cualquier despliegue que no
        seteara GODML_VERSION —o sea, casi todos— reportaba "dev" y el endpoint
        no servía para saber qué versión estaba sirviendo.
        """
        from fastapi.testclient import TestClient

        from godml import __version__
        from godml.deploy_service.server import app

        monkeypatch.delenv("GODML_VERSION", raising=False)
        # Sin context manager: evita el startup, que buscaría un modelo en disco.
        respuesta = TestClient(app).get("/version").json()

        assert respuesta["godml_version"] == __version__
        assert respuesta["godml_version"] != "dev"

    def test_la_variable_de_entorno_sigue_teniendo_prioridad(self, monkeypatch):
        from fastapi.testclient import TestClient

        from godml.deploy_service.server import app

        monkeypatch.setenv("GODML_VERSION", "build-42")
        assert TestClient(app).get("/version").json()["godml_version"] == "build-42"
