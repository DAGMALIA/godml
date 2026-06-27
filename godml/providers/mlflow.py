# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# Licensed under the MIT License

import os
import pandas as pd
from sklearn.model_selection import train_test_split
from godml.core_service.engine import BaseExecutor
from godml.config_service.schema import PipelineDefinition, ModelResult
from godml.model_service.model_loader import load_custom_model_class
from godml.monitoring_service.logger import get_logger
from godml.utils.path_utils import normalize_path
from godml.utils.predict_safely import predict_safely
from godml.utils.log_model_generic import log_model_generic
from godml.monitoring_service.metrics import evaluate_binary_classification

logger = get_logger()


class MLflowExecutor(BaseExecutor):
    def __init__(self, tracking_uri: str = None):
        import mlflow  # lazy — only load when executor is actually used
        if tracking_uri:
            if tracking_uri.startswith("file:/"):
                local_path = tracking_uri.replace("file:/", "", 1)
                normalized = normalize_path(local_path)
                tracking_uri = f"file://{normalized}"
            mlflow.set_tracking_uri(tracking_uri)
        else:
            mlflow.set_tracking_uri("file:./mlruns")

        mlflow.set_experiment("godml-experiment")

    def preprocess_for_xgboost(self, df, target_col="target"):
        if target_col not in df.columns:
            raise ValueError("El dataset debe contener una columna llamada 'target'.")
        if df[target_col].dtype == object:
            df[target_col] = df[target_col].map({"Yes": 1, "No": 0})

        y = df[target_col]
        X = df.drop(columns=[target_col])

        cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
        if cat_cols:
            X = pd.get_dummies(X, columns=cat_cols, drop_first=True)
        return X, y

    def run(self, pipeline: PipelineDefinition):
        import mlflow
        import mlflow.models.signature
        from godml import notebook_api as nb
        logger.info(f"🚀 INICIO DE PIPELINE: {pipeline.name}")

        # ╭───────────────────────────────
        # 1️⃣ Dataset + DataPrep (si existe)
        # ────────────────────────────────╮
        ds = pipeline.dataset
        dataset_path = ds.uri
        dataset_path_abs = os.path.abspath(dataset_path)

        logger.info(
            f"""
    📂 Dataset Configuration
    ────────────────────────────────────────
      • CWD               : {os.getcwd()}
      • dataset.uri       : {dataset_path}
      • abs path          : {dataset_path_abs}
      • target column     : {getattr(ds, 'target', None)}
      • dataprep presente : {bool(getattr(ds, 'dataprep', None))}
    """
        )

        if str(dataset_path).startswith("s3://"):
            raise ValueError("MLflowExecutor solo soporta datasets locales (CSV).")

        dataprep_payload = getattr(ds, "dataprep", None)
        if dataprep_payload:
            try:
                logger.info("🧪 Ejecutando DataPrep embebido (dataset.dataprep)...")
                df = nb.dataprep_run_inline(dataprep_payload)
                clean_dir = os.path.dirname(dataset_path_abs)
                os.makedirs(clean_dir, exist_ok=True)
                df.to_csv(dataset_path_abs, index=False)
                logger.info(f"✅ Dataset limpio guardado en: {dataset_path_abs}")
            except Exception as e:
                logger.error(f"❌ Falló DataPrep embebido: {e}")
                raise
        else:
            logger.info(f"📥 Cargando dataset limpio desde ruta: {dataset_path_abs}")
            if not os.path.exists(dataset_path_abs):
                raise FileNotFoundError(
                    f"No existe el archivo limpio en dataset.uri.\n"
                    f"  - dataset.uri: {dataset_path}\n"
                    f"  - abs: {dataset_path_abs}\n"
                    f"  - cwd: {os.getcwd()}\n"
                    f"Sugerencias:\n"
                    f"  * Define 'dataset.dataprep' en el YAML para generarlo automáticamente.\n"
                    f"  * O crea previamente el archivo en esa ruta."
                )
            df = pd.read_csv(dataset_path_abs)

        # ╭───────────────────────────────
        # 2️⃣ Target (obligatorio)
        # ────────────────────────────────╮
        target = getattr(ds, "target", None)
        if not target:
            raise ValueError(
                "El campo 'dataset.target' es obligatorio en el YAML del pipeline. "
                "Ejemplo:\n"
                "  dataset:\n"
                "    uri: ./data/train.csv\n"
                "    target: mi_columna_objetivo"
            )

        if target not in df.columns:
            raise ValueError(f"El dataset no contiene la columna target '{target}'.")

        logger.info(f"🎯 Columna objetivo detectada: {target}")

        # ╭───────────────────────────────
        # ⚖️ Cumplimiento normativo (PCI-DSS, etc.) + saneo de dtypes
        # ────────────────────────────────╮

        def _sanitize_dtypes_after_compliance(df_in: pd.DataFrame, target_col: str) -> pd.DataFrame:
            """
            Convierte cualquier columna no numérica en algo aceptable por XGBoost:
            - Si la col es el target, no se toca.
            - Si es object/category: se codifica como category.codes (int).
            - En último caso se dropea si sigue siendo no numérica.
            """
            df_out = df_in.copy()
            for col in df_out.columns:
                if col == target_col:
                    continue
                if df_out[col].dtype == "O":  # object → category.codes
                    try:
                        df_out[col] = df_out[col].astype("category").cat.codes
                    except Exception:
                        df_out.drop(columns=[col], inplace=True)
                elif str(df_out[col].dtype).startswith("category"):
                    df_out[col] = df_out[col].cat.codes
            return df_out

        try:
            from godml.core_service.pipeline_runner import run_pipeline_preprocessing
            from godml.utils.path_utils import normalize_path, validate_safe_path

            # Ejecuta preprocesamiento centralizado (aplica ComplianceEngine y guarda compliant_output si viene)
            logger.info("🧩 Ejecutando preprocesamiento del pipeline (compliance, guardado opcional)...")
            df = run_pipeline_preprocessing(pipeline, df)

            # Si el runner guardó a dataset.compliant_output, úsalo como dataset.uri para el resto del flujo
            compliant_output = getattr(pipeline.dataset, "compliant_output", None)
            if compliant_output:
                try:
                    normalized = normalize_path(compliant_output)
                    validate_safe_path(normalized, base_dir=os.getcwd())
                    if os.path.exists(normalized):
                        pipeline.dataset.uri = compliant_output
                        logger.info(f"✅ Dataset compliant asignado para entrenamiento: {normalized}")
                    else:
                        logger.warning(f"⚠️ 'dataset.compliant_output' definido pero no existe en disco: {normalized}")
                except Exception as e:
                    logger.warning(f"⚠️ Validación de ruta compliant_output falló: {e}")

            # Post-compliance: garantiza que XGBoost no reciba columnas object
            df = _sanitize_dtypes_after_compliance(df, target)

            # Log informativo de tipos
            non_numeric = [c for c in df.drop(columns=[target]).columns
                           if df[c].dtype == "O" or str(df[c].dtype).startswith("category")]
            if non_numeric:
                logger.warning(f"⚠️ Aún hay columnas no numéricas tras saneo: {non_numeric} (se intentó codificar).")

        except Exception as e:
            logger.warning(f"⚠️ Error en preprocesamiento/compliance centralizado: {e}")


        # ╭───────────────────────────────
        # 3️⃣ Split (estratificado si aplica)
        # ────────────────────────────────╮
        X = df.drop(columns=[target])
        y = df[target]

        is_classif = getattr(y, "nunique", lambda: 2)() <= 20
        strat = y if is_classif else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=strat
        )
        logger.info(f"✅ Split completado: train={len(X_train)}, test={len(X_test)}")

        # ╭───────────────────────────────
        # 4️⃣ Hiperparámetros y carga del modelo
        # ────────────────────────────────╮
        params = pipeline.model.hyperparameters.model_dump(exclude_none=True)
        model_type = pipeline.model.type.lower()

        from godml.model_service.auto_tuner import auto_tune_hyperparameters

        params = pipeline.model.hyperparameters.model_dump(exclude_none=True)
        model_type = pipeline.model.type.lower()
        
        # 🧠 Ajuste automático basado en tipo de modelo y dataset
        params = auto_tune_hyperparameters(model_type, params, X_train, y_train)


        project_path = os.getcwd()

        # Solo cargar el modelo una vez
        source = getattr(pipeline.model, "source", "local")
        model_loaded = False
        try:
            model_instance = load_custom_model_class(project_path, model_type, source)
            if not model_loaded:
                logger.info(f"✅ Modelo {model_type} cargado desde {source}")
                model_loaded = True
        except Exception as e:
            logger.error(f"❌ Error al cargar el modelo '{model_type}': {e}")
            raise

        max_attempts = 3
        try:
            for attempt in range(max_attempts):
                with mlflow.start_run(run_name=f"{pipeline.name}_attempt_{attempt+1}"):

                    # ──────────────────────────────────────
                    # Etiquetas y artefactos
                    # ──────────────────────────────────────
                    if os.path.exists(dataset_path):
                        mlflow.log_artifact(dataset_path, artifact_path="dataset")
                    mlflow.set_tag("dataset.uri", pipeline.dataset.uri)
                    mlflow.set_tag("version", pipeline.version)
                    mlflow.set_tag("dataset.target", target)
                    if getattr(pipeline, "description", None):
                        mlflow.set_tag("description", pipeline.description)
                    if getattr(pipeline.governance, "owner", None):
                        mlflow.set_tag("owner", pipeline.governance.owner)
                    if getattr(pipeline.governance, "tags", None):
                        for tag_dict in pipeline.governance.tags:
                            for k, v in tag_dict.items():
                                mlflow.set_tag(k, v)
                    for param_name, param_value in params.items():
                        mlflow.log_param(param_name, param_value)

                    # ╭───────────────────────────────
                    # 5️⃣ Entrenamiento
                    # ────────────────────────────────╮
                    train_result = model_instance.train(X_train, y_train, X_test, y_test, params)

                    if isinstance(train_result, tuple):
                        if len(train_result) == 3:
                            model, preds, metrics_dict = train_result
                        elif len(train_result) == 2:
                            model, preds = train_result
                            metrics_dict = evaluate_binary_classification(y_test, preds)
                        else:
                            raise ValueError("❌ El método 'train' retornó una tupla con longitud inesperada.")
                    else:
                        raise ValueError("❌ El método 'train' debe retornar al menos (modelo, predicciones).")

                    input_example = X_train.iloc[:5]
                    output_example = predict_safely(model, input_example)
                    signature = mlflow.models.signature.infer_signature(input_example, output_example)

                    metrics_dict = evaluate_binary_classification(y_test, preds)
                    for metric_name, value in metrics_dict.items():
                        mlflow.log_metric(metric_name, value)

                    logger.info(
                        "📊 Métricas de entrenamiento\n"
                        "────────────────────────────────────────\n"
                        + "\n".join([f"  • {k:<10} : {v:.4f}" for k, v in metrics_dict.items()])
                    )
                    logger.info(f"✅ Entrenamiento finalizado. AUC: {metrics_dict.get('auc', 0):.4f}")

                    # ╭───────────────────────────────
                    # 6️⃣ Validación por thresholds
                    # ────────────────────────────────╮
                    all_metrics_passed = True
                    for metric in pipeline.metrics:
                        value = metrics_dict.get(metric.name)
                        if value is None:
                            logger.warning(f"⚠️ Métrica '{metric.name}' no fue calculada.")
                            continue
                        if value < metric.threshold:
                            logger.error(f"🚫 {metric.name.upper()} ({value:.4f}) < {metric.threshold}")
                            all_metrics_passed = False

                    # ╭───────────────────────────────
                    # 7️⃣ Registro del modelo y batch output
                    # ────────────────────────────────╮
                    output_path = None
                    if all_metrics_passed:
                        log_model_generic(
                            model,
                            model_name="model",
                            registered_model_name=f"{pipeline.name}-{model_type}",
                            input_example=input_example,
                            signature=signature,
                        )
                        logger.info(f"✅ Modelo registrado exitosamente: {pipeline.name}-{model_type}")

                        if getattr(pipeline, "deploy", None) and pipeline.deploy.batch_output:
                            output_path = os.path.abspath(pipeline.deploy.batch_output)
                            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                            pd.DataFrame({"prediction": preds}).to_csv(output_path, index=False)
                            logger.info(f"📦 Predicciones guardadas en: {output_path}")

                            # 🆕 Guardar modelo local .pkl si el YAML lo define
                            if getattr(pipeline, "deploy", None) and getattr(pipeline.deploy, "model_output", None):
                                from godml.utils.path_utils import normalize_path, validate_safe_path
                                import joblib

                                try:
                                    model_output_path = normalize_path(pipeline.deploy.model_output)
                                    validate_safe_path(model_output_path)
                                    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
                                    joblib.dump(model, model_output_path)

                                    logger.info(f"💾 Modelo guardado en formato .pkl: {model_output_path}")
                                except Exception as e:
                                    logger.error(f"❌ No se pudo guardar el modelo .pkl: {e}")

                        # 📈 BLOQUE FINAL DE RESUMEN
                        logger.info(
                            "\n📈 Final del pipeline\n"
                            "────────────────────────────────────────\n"
                            f"  • Estado   : ✅ Éxito\n"
                            f"  • Modelo   : {pipeline.name}-{model_type}\n"
                            f"  • AUC      : {metrics_dict.get('auc', 0):.4f}\n"
                            f"  • Output   : {output_path or 'N/A'}\n"
                        )

                        return ModelResult(
                            model=model,
                            predictions=preds,
                            metrics=metrics_dict,
                            output_path=output_path,
                            model_path=locals().get("model_output_path", None),
                        )

                    else:
                        logger.error(
                            "\n🚨 RESULTADO DEL PIPELINE: MÉTRICAS INSUFICIENTES 🚨\n"
                            "══════════════════════════════════════════════════════════════════════\n"
                            "⚠️  Las métricas no alcanzaron los umbrales esperados.\n"
                            "💡  Recomendaciones:\n"
                            "    • Ajusta los thresholds en godml.yml\n"
                            "    • Mejora la calidad del dataset (usa dataset.dataprep)\n"
                            "    • Prueba otros hiperparámetros (AutoTuning)\n"
                            "══════════════════════════════════════════════════════════════════════"
                        )
                        raise RuntimeError("❌ Las métricas no alcanzaron los umbrales esperados.")

        except Exception as e:
            logger.error(
                "\n📉 Final del pipeline\n"
                "────────────────────────────────────────\n"
                f"  • Estado   : ❌ Fallo\n"
                f"  • Error    : {str(e)}\n"
                f"  • Modelo   : {pipeline.name}-{model_type}\n"
            )
            raise

    # ==========================================================
    # 🔍 VALIDATE (sin cambios de lógica)
    # ==========================================================
    def validate(self, pipeline: PipelineDefinition):
        errors = []
        warnings_ = []

        try:
            from godml.core_service.validators import validate_pipeline
            ext_warns = validate_pipeline(pipeline)
            for w in ext_warns:
                warnings_.append(str(w))
        except Exception:
            pass

        ds = getattr(pipeline, "dataset", None)
        if ds is None:
            errors.append("dataset: faltante en el pipeline.")
        else:
            uri = getattr(ds, "uri", None)
            dataprep = getattr(ds, "dataprep", None)
            target = getattr(ds, "target", None)
            if not dataprep:
                if not uri:
                    errors.append("dataset.uri: faltante (o define dataset.dataprep).")
                else:
                    try:
                        from pathlib import Path
                        p = Path(str(uri))
                        if not p.exists():
                            errors.append(f"dataset.uri: archivo no encontrado -> {uri}")
                    except Exception as e:
                        warnings_.append(f"No se pudo validar dataset.uri ('{uri}'): {e}")
            if not target:
                warnings_.append(
                    "dataset.target no definido. Se aplicará heurística: 'survived'/'Survived'."
                )

        model = getattr(pipeline, "model", None)
        if model is None:
            errors.append("model: faltante en el pipeline.")
        else:
            model_type = getattr(model, "type", None)
            source = getattr(model, "source", "core")
            if not model_type or not isinstance(model_type, str):
                errors.append("model.type: faltante o inválido.")
            else:
                try:
                    import logging
                    # 🔇 Silenciamos logs temporalmente
                    previous_level = logger.level
                    logger.setLevel(logging.ERROR)
                    project_path = os.getcwd()
                    _ = load_custom_model_class(project_path, model_type.lower(), source)
                    logger.setLevel(previous_level)
                except Exception as e:
                    logger.setLevel(previous_level)
                    errors.append(f"model: no se pudo cargar '{model_type}' desde source='{source}': {e}")

        for w in warnings_:
            logger.warning(f"⚠️ {w}")
        if errors:
            msg = " | ".join(errors)
            logger.error(f"❌ Validación de pipeline falló: {msg}")
            raise ValueError(f"Validación de pipeline falló: {msg}")

        logger.info("✅ Validación de pipeline completada sin errores bloqueantes.")
