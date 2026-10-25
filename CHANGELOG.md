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

### Changed

- License text: the `LICENSE` file now contains the MIT license. GoDML has
  always been distributed under MIT (package metadata, README and source
  headers); the Apache-2.0 text that appeared in `LICENSE` was re-added by
  mistake and did not reflect the project's license.
- Package metadata uses the SPDX license expression `MIT` (PEP 639), and
  source headers use `SPDX-License-Identifier: MIT`.
