# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.4.0] - Unreleased

### Upgrading from 1.3.x

1.4.0 is fail-closed: several checks that used to log and continue now stop
the run. Review these before upgrading (details in the sections below):

- **Unsupported `governance.compliance` values abort.** Anything other than
  `pci-dss` was skipped silently, so that data was never protected. Use
  `pci-dss` or remove the key.
- **Governance validation blocks.** A blank `governance.owner`, an
  out-of-range metric threshold or a batch deploy without
  `deploy.batch_output` now fail `godml run`.
- **A pinned `dataset.hash` is verified.** `godml run` fails if the file at
  `dataset.uri` does not match it. Re-pin with
  `godml calc-hash <file> --update-yaml <godml.yml>` when the change is
  intended. With `provider: sagemaker` the hash is **not** verified for S3
  data yet; a warning says so.
- **SageMaker never applied compliance**, and `governance.compliance` with
  `provider: sagemaker` is now rejected at validation. Until the official 2.0
  image: apply compliance locally, upload the processed data to S3 and run
  SageMaker without the `compliance` key.
- **MLflow runs from 1.x may contain the raw dataset** under the `dataset/`
  artifact path. Review and delete those artifacts if they hold personal data.
- **Compliance requires `GODML_PII_KEY`.** Whenever `governance.compliance`
  is set (any policy, any environment) the run stops without it. Generate one
  with `python -c "import secrets; print(secrets.token_hex(32))"` and use the
  same key for training and serving. `GODML_ALLOW_INSECURE_PII_KEY=1` allows a
  public dev key outside prod, for throwaway tests only. `hash_sensitive` is
  now an HMAC-SHA256 keyed by it, so hashed values differ from 1.x: retrain
  models that use hashed columns as features and re-hash stored lookups.
- **PII detection changed.** Ordinary columns that 1.x dropped or hashed by
  mistake (`hotel_id`, `plate`, `tip`, `year`, `fare`, any 5-digit amount,
  any 4-decimal float, ...) are now kept, so models trained with
  `drop_sensitive`/`hash_sensitive` may see new features: retrain and
  compare. CVV, zip/postal codes and coordinates are now detected only when
  the column name says so (`cvv`, `zip_code`, `lat`, ...): rename such
  columns if they have generic names. The dataset target is never treated as
  PII.
- **Loss-metric thresholds are upper bounds.** For `mse`, `rmse`, `mae` and
  `log_loss` a run passes when the value is `<=` the threshold (1.x required
  `>=`, so good models were rejected and bad ones registered). Review
  thresholds you tuned around the old behavior.
- **Library logging is silent by default.** Outside the CLI (notebooks,
  scripts), godml no longer prints its own log lines or writes
  `logs/godml.log`. To see them, configure logging in your application, e.g.
  `logging.basicConfig(level=logging.INFO)`. The `godml` CLI output is
  unchanged.

### Security

- Compliance is now fail-closed. When `governance.compliance` is set and
  cannot be applied, `godml run` aborts with `ComplianceError`
  (`godml.compliance_service.errors`) instead of logging the error and
  training on the unprocessed data. This covers engine failures, a missing
  compliance engine and unsupported standards: a YAML with
  `compliance: gdpr` (or any value other than `pci-dss`) now fails instead of
  being silently skipped. Applies to `ComplianceEngine.apply`,
  `run_pipeline_preprocessing`, the MLflow executor and the dataprep recipe
  hook.

  **Action required if your YAML sets an unsupported standard:** data
  processed with it was never protected by that standard (earlier versions
  skipped it silently). Set `governance.compliance: pci-dss` or remove the
  `compliance` key.

- The MLflow executor no longer uploads the source dataset (`dataset.uri`) as
  a run artifact. That file is read before compliance, so the upload exposed
  raw PII even with PCI-DSS configured. Runs now log
  `dataset/dataset_metadata.json` (source SHA-256, row count and column
  types). Set `dataset.log_dataset: true` to also upload the training data
  after compliance (`dataset/compliant_dataset.csv`).

  **Action required if you used MLflow with 1.x:** earlier runs may contain
  the raw dataset under the `dataset/` artifact path; review and delete those
  artifacts from your tracking server if they hold personal data.

- `godml run` now enforces the governance validation it already ran: a blank
  `governance.owner`, a metric threshold outside its valid range or a batch
  deploy without `deploy.batch_output` stop the run with `ValidationError`.
  The MLflow executor used to swallow that error (`except Exception: pass`).

- SageMaker: compliance never ran. The preprocessing script called a
  non-existent API, ignored the policy and turned any failure into a warning;
  and the stock sklearn processing image does not include godml, so the
  compliance step was always skipped and training received unprocessed data.
  `provider: sagemaker` with `governance.compliance` is now rejected at
  validation, before any AWS job is created, and the script itself aborts if
  compliance cannot be applied.

  **Action required if you use SageMaker with compliance:** apply compliance
  before uploading the data to S3 (for example with `godml dataprep`) and
  remove `governance.compliance` from that pipeline, or use
  `provider: mlflow`. Review data already used in SageMaker training jobs.

- A pinned `dataset.hash` is now verified by `godml run` (MLflow executor)
  before the data is used; a mismatch stops the run with
  `DatasetIntegrityError` showing both hashes. Before, only `"auto"` vs. a
  value was checked and any file was accepted. `auto` or empty still skips the
  check. The SageMaker executor warns that S3 data is not verified.

- SageMaker evaluation step: the model-archive path-traversal check used a
  string prefix, so a member such as `../model_evil/x` could be written to a
  sibling directory of the model dir, and symlinks/hardlinks were not
  checked. Members are now resolved with `Path.resolve()` and must be
  `is_relative_to` the model dir; links are rejected.

- Path containment checks compared strings with `startswith`, so a sibling
  directory sharing the prefix (`/proj-evil` for `/proj`) counted as inside
  the project: the CLI's absolute-path check, `validate_model_path` in the
  deploy service and in the scaffold template copied into user projects, and
  the local model loader (which imports a `.py` file). They now use
  `Path.resolve()` + `is_relative_to`, and the CLI resolves its base dirs on
  each call instead of once at import. The local model loader also rejects a
  symlinked `models/` directory pointing outside the project. Projects generated with
  `godml deploy` before 1.4.0 keep the old template: regenerate
  `deploy_service/` to get the fix.

- PII hashing (`hash_sensitive` and the unknown-policy fallback) used an
  unkeyed SHA-256 truncated to 12 hex chars, which can be reversed by brute
  force or a dictionary for card numbers and emails. It is now an
  HMAC-SHA256 keyed by `GODML_PII_KEY`, which is required whenever
  compliance runs (`ComplianceError` otherwise; opt-out
  `GODML_ALLOW_INSECURE_PII_KEY=1` outside prod only).

- PCI-DSS PII detection matched name hints as substrings (`tel` in
  `hotel_id`, `lat` in `plate`, `ip` in `tip`/`description`, `name` in
  `filename`) and treated any 3-4 digit number as a CVV, any 5-digit number
  as a zip code and any float with 4 decimals as a coordinate, so ordinary
  features were dropped or hashed, including the target. Name hints now
  match whole tokens (snake_case and camelCase), those ambiguous content
  patterns need a confirming column name, expiration dates need a `/`, and
  the target column is excluded (`exclude_columns`).

- The scaffold inference server (`godml deploy` template) logged every
  request's feature values, so PII reached the service logs. It now logs only
  the shape and column names. Projects generated before 1.4.0 keep the old
  template: regenerate `deploy_service/`.

- The Safety dependency scan never audited anything: it scanned
  `pyproject.toml` ranges and its policy ignored every unpinned requirement
  ("92 vulnerabilities found, 92 ignored due to policy"), its `--ignore`
  list was not a `safety scan` option, and the step ran with
  `continue-on-error`. Safety now blocks CI (audit job and release pipeline),
  scans the pinned environment CI installs, and applies only the 3 reviewed
  ignores in `.safety-policy.yml` (listed in SECURITY.md); the 15 ignores
  of 1.x no longer apply and were removed. Because `safety scan` always
  applies the Safety Platform policy, a gate script in the repository
  enforces those ignores on the scan report.

### Fixed

- pandas 3 support in the MLflow executor: text columns are now inferred as
  `str` (not `object`), so the post-compliance sanitizer left them unencoded
  and XGBoost rejected the training data. Text detection now covers both.
- `MLFLOW_TRACKING_URI=file:...`: the executor maps it to a SQLite store
  (`<dir>/mlflow.db`, since MLflow 3 dropped the file store). It now creates
  the directory (it failed with `OperationalError` when missing), keeps
  absolute POSIX paths absolute and decodes `%20`-style escapes (before,
  `file:///home/u/mlruns` became the cwd-relative `home/u/mlruns`), and logs
  the conversion.
- Importing godml no longer changes the host process: no global warning
  filters, no TensorFlow env vars (`TF_CPP_MIN_LOG_LEVEL`,
  `TF_ENABLE_ONEDNN_OPTS`), no root or third-party logger configuration, no
  `logs/` directory, and TensorFlow/LightGBM are no longer imported just to
  detect model types. Library loggers only have a `NullHandler`; the CLI
  configures output (`configure_cli_logging`) and sets the TensorFlow env
  vars as defaults.
- Metric thresholds now have a direction. Loss metrics (`mse`, `rmse`, `mae`,
  `log_loss`) pass when `<=` the threshold in the MLflow registration gate,
  the CLI metrics table and the SageMaker RegisterModel condition; before,
  every metric needed `>=`, so with `mse: 0.5` an error of 0.1 failed and
  2.0 passed. `log_loss` thresholds are no longer limited to [0, 1].
- `${VAR}` interpolation in `godml.yml`: values inside lists of dicts or
  nested lists (e.g. `governance.tags`, `metrics`) are now resolved, and a
  variable inside a longer string keeps the rest of it
  (`s3://${BUCKET}/data.csv` used to become just the bucket name; several
  variables per value now work). An unset variable without default inside a
  longer string raises `ConfigurationError`; a value that is exactly
  `${VAR}` still becomes empty (None) as in 1.x.
- `godml deploy` published `-p <port>:<port>`, but the generated image always
  listens on 8000, so any environment whose `deploy_config.<env>.port` was
  not 8000 (e.g. qa 8001, prod 80) was unreachable. It now publishes
  `<port>:8000`. `godml serve` runs uvicorn with auto-reload only in `dev`.
- Inference servers (`deploy_service` and the scaffold template): request
  features are reordered to the training order (`feature_names_in_` or the
  Booster's `feature_names`) and unknown keys are ignored. Before, a payload
  whose JSON keys came in another order failed (sklearn) or did not match
  the Booster's features, and an extra key broke the request. A missing
  feature is a 400. `/predict` also returns `probabilities` when the model
  has `predict_proba` (the `prediction` field is unchanged).
- `godml --help` (and any CLI output) no longer crashes with
  `UnicodeEncodeError` when the terminal or redirected output is not UTF-8
  (Windows cp1252 consoles, CI logs): characters the stream cannot encode are
  printed as `?`. The emoji in the `dataprep` help text was removed.
- RandomForest (and other scikit-learn models) could not be logged to MLflow
  with recent MLflow versions (skops serialization): the sklearn branch of
  the model logger never passed `skops_trusted_types`, and the allowlist only
  covered XGBoost, so `sklearn.tree._tree.Tree` was rejected. All sklearn-API
  models now go through the same path with a reviewed allowlist.
- `godml[aws]` allowed SageMaker Python SDK v3, which removed the
  `sagemaker.workflow`, `sagemaker.processing` and `sagemaker.image_uris`
  modules the SageMaker executor uses, so a fresh install had a broken
  executor. The extra now requires `sagemaker>=2.257.2,<3` (2.257.2 fixes
  PYSEC-2026-3059/3060).

### Changed

- Every release is smoke-tested after publication: `post_publish_smoke.yml`
  installs `godml[all]==<version>` from PyPI in a clean environment and runs
  `godml --help`, `godml init`, `godml run`, and `godml run` without
  `GODML_PII_KEY` (must fail). A final version is only tagged once its latest
  release candidate passed this test.
- `pre-commit` is no longer part of the `dev` extra: install it with
  `pipx install pre-commit`. Its patched `virtualenv` requires
  `packaging>=26.3`, which conflicts with the patched SageMaker SDK
  (`packaging<25`), so one environment could not hold both without CVEs.
- README rewritten to document only what exists and works: removed the GDPR,
  HIPAA and SOX claims (only PCI-DSS is implemented) and the non-existent
  `GdprCompliance`, `GodmlNotebook.load_data/train_model/evaluate` and model
  aliases `xgb`/`rf`/`logreg`; fixed the notebook, `tune_model` (`roc_auc`,
  numeric features) and advisor (`[advisor]` extra, prints a report)
  examples; listed every CLI command; corrected the release asset names
  (`multiple.intoto.jsonl`, `sbom.cyclonedx.json`); the quick start explains
  adding data and `dataset.target`. A test runs the README examples.
- `godml init` writes `dataset.target` in `godml.yml` and its next steps say
  to add the data and set the target. The generated project README no longer
  carries an MIT badge or "Python 3.8+", and its examples use `target` and
  the real CLI command names.
- License text: the `LICENSE` file now contains the MIT license. GoDML has
  always been distributed under MIT (package metadata, README and source
  headers); the Apache-2.0 text that appeared in `LICENSE` was re-added by
  mistake and did not reflect the project's license.
- Package metadata uses the SPDX license expression `MIT` (PEP 639), and
  source headers use `SPDX-License-Identifier: MIT`.
