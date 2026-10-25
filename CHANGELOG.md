# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.4.0] - Unreleased

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

### Fixed

- pandas 3 support in the MLflow executor: text columns are now inferred as
  `str` (not `object`), so the post-compliance sanitizer left them unencoded
  and XGBoost rejected the training data. Text detection now covers both.

### Changed

- License text: the `LICENSE` file now contains the MIT license. GoDML has
  always been distributed under MIT (package metadata, README and source
  headers); the Apache-2.0 text that appeared in `LICENSE` was re-added by
  mistake and did not reflect the project's license.
- Package metadata uses the SPDX license expression `MIT` (PEP 639), and
  source headers use `SPDX-License-Identifier: MIT`.
