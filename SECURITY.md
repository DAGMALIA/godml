# 🔐 GODML Security & Supply Chain Policy

[![SBOM](https://img.shields.io/badge/SBOM-CycloneDX%20%2B%20SPDX-blue)](#-release-artifacts)
[![SLSA Provenance](https://img.shields.io/badge/SLSA-L3%20provenance-orange)](#-release-artifacts)
[![Trusted Publisher](https://img.shields.io/badge/PyPI-Trusted%20Publisher-purple)](#-release-artifacts)

This document describes the controls that are **actually enforced today** in
this repository's CI/CD. Planned improvements are listed separately and are
not claimed as implemented.

## 🧱 Overview

Two workflows build and publish GODML:

- **`safety_scan.yml`** (every push to `main`; the file name is historical):
  tests, Bandit, Safety, pip-audit, SPDX SBOM signed with Cosign, then pushes the
  `v<version>` tag.
- **`release.yml`** (on that tag): builds sdist and wheel, generates a
  CycloneDX SBOM and SLSA L3 provenance, creates the GitHub Release and
  publishes to PyPI with Trusted Publishing (OIDC, no API token).

`ci.yml` runs on every push and pull request to `main`/`develop`.

---

## 🧪 Security Scans

| Tool | Purpose | Where | Enforcement |
|------|---------|-------|-------------|
| **Bandit** | Insecure code patterns | `ci.yml` (SAST job), `safety_scan.yml` | **Blocking** on HIGH severity (`-lll`). MEDIUM/LOW are reported in SARIF, not blocking |
| **Safety** | Dependency CVEs (Safety DB) | `ci.yml` (audit job), `safety_scan.yml` | **Blocking**, any severity, ignores only those listed below (`.safety-policy.yml`) |
| **pip-audit** | Dependency CVEs (PyPI advisory DB / OSV) | `ci.yml` (core install), `safety_scan.yml` (dev install) | **Blocking**, no ignored IDs |
| **ruff** (`S110`, `BLE001`) + **mypy** | No silent `except Exception: pass`, no blind excepts, type checks | `ci.yml` (lint job), pre-commit | **Blocking** for new code. Pre-existing cases are tagged `# noqa` as tracked debt |

Scan reports (Bandit, pip-audit, signed SPDX SBOM) are uploaded as the
`supplychain-artifacts` workflow artifact of **“🔐 GODML Supply Chain + PyPI
Release”**. Bandit SARIF is also sent to the repository's Security tab.

---

## 📦 Release Artifacts

| Artifact | Format | Signed | Where |
|----------|--------|--------|-------|
| Wheel and sdist | `.whl`, `.tar.gz` | Covered by SLSA provenance | GitHub Release + PyPI |
| SLSA provenance | `multiple.intoto.jsonl` (SLSA L3, `slsa-github-generator`) | ✅ Sigstore | GitHub Release |
| SBOM | CycloneDX JSON (`sbom.cyclonedx.json`) | ❌ | GitHub Release |
| SBOM | SPDX JSON (`sbom.spdx.json`) | ✅ Cosign keyless (OIDC → Rekor) | Workflow artifact only, not on the Release |

---

## 🔗 Dependency Locking

- `requirements.lock` was generated with `pip-compile` from `pyproject.toml`
  (last regenerated 2025-10-29). It **does not contain hashes** and CI does
  **not** install from it.
- pip-audit audits the environment CI actually resolves, not the committed
  lockfile.
- CI installs from the version ranges in `pyproject.toml`. A reproducible
  lockfile with hashes is planned (GoDML 2.0 plan, F8-02).

---

## 🧾 Known Vulnerabilities & Accepted Risks

Two scanners block CI: **Safety** and **pip-audit**. Both scan the
environment CI actually installs (Safety scans a pinned `pip freeze`; it no
longer ignores unpinned or environment results).

**pip-audit:** no ignored advisories.

**Safety:** exactly these ignores, defined in `.safety-policy.yml`:

| Safety ID | Package | CVE | Issue | Expires |
|-----------|---------|-----|-------|---------|
| 71577 | mlflow | CVE-2024-37052 | Loading a malicious scikit-learn model executes code | 2027-01-23 |
| 71578 | mlflow | CVE-2024-37053 | Loading a malicious scikit-learn model executes code | 2027-01-23 |
| 71587 | mlflow | CVE-2024-37054 | Loading a malicious PyFunc model executes code | 2027-01-23 |
| 71693 | mlflow | CVE-2024-37055 | Loading a malicious pmdarima model executes code | 2027-01-23 |
| 71584 | mlflow | CVE-2024-37056 | Loading a malicious LightGBM model executes code | 2027-01-23 |
| 71692 | mlflow | CVE-2024-37057 | Loading a malicious TensorFlow model executes code | 2027-01-23 |
| 71691 | mlflow | CVE-2024-37059 | Loading a malicious PyTorch model executes code | 2027-01-23 |
| 71579 | mlflow | CVE-2024-37060 | Loading a malicious MLflow Recipe executes code | 2027-01-23 |

Why they are accepted: MLflow deserializes model files (pickle /
cloudpickle) and no fixed MLflow version exists (all affect the resolved
mlflow 3.17.2). GoDML only loads models it trained itself, from validated
paths, and does not run an MLflow server accepting third-party uploads.

Revalidated on 2026-10-25 against the versions CI resolves. Seven IDs ignored
in 1.x (`71701`, `71703`, `71706`, `71707`, `62727`, `62800`, `62801`) could
not be matched to any package in the public Safety DB and were **removed**:
if they apply, the blocking scan reports them for review.

**Review policy:** at every release and at most every 90 days (the
`expires` date makes Safety report them again). An ignore stays only while
the advisory still applies to the resolved versions and the reason holds.

`safety scan` prefers a policy stored in Safety Platform for the `godml`
project over `.safety-policy.yml`; the platform project must not override
it, otherwise the list above is not what is applied.

(`PYSEC-2024-230`, a certifi advisory fixed in
2024.7.4, was ignored until 2026-10-24 and no longer applied.)

Mitigations for MLflow-related risk: GODML is meant to load only models its
own pipeline produced. The deploy service checks model paths
(`validate_model_path`), but that check has a known weakness being fixed in
1.4.0 (plan F1-13); until then, only serve models from directories you
control.

---

## 🌐 Network Exposure

The generated deploy service binds to `0.0.0.0` by default (dev, qa and prod
configs, and `HOST` in `deploy_service/main.py`) so that it is reachable from
inside a container. Set `HOST` (or the `host` key in the deploy config) to
restrict it when running outside a container.

---

## 🧰 Reporting Security Issues

If you believe you’ve found a security vulnerability in GODML:

1. **Do not open a public issue.**
2. Please contact the security team privately:
 - 📧 **security@dagmalia.com**
 - or directly to maintainer: **Arturo Gutierrez Rubio Rojas (agtzrubio@dagmalia.com)**

Reports will be acknowledged within **72 hours**, and mitigation steps will be tracked publicly once verified.

---

## 🔒 Responsible Disclosure Policy

GODML adheres to the principles of **responsible disclosure**:
- Vulnerabilities are not disclosed publicly until a fix or mitigation is available.
- Credits will be given to researchers who responsibly report verified issues.
- Reproducible PoC submissions are encouraged for efficient triage.

---

## 🧬 Supply Chain Integrity Summary

| Component | Control | Status |
|-----------|---------|--------|
| Build provenance | SLSA L3 (`slsa-github-generator`), attached to the Release | ✅ Implemented |
| SBOM | CycloneDX on the Release; SPDX signed with Cosign as workflow artifact | ✅ Implemented (signed SBOM not yet on the Release) |
| PyPI publishing | Trusted Publisher (OIDC) | ✅ Implemented |
| Code scanning | Bandit HIGH blocking; ruff fail-closed rules for new code | ✅ Implemented |
| Dependency scanning | Safety + pip-audit, both blocking; 8 reviewed Safety ignores | ✅ Implemented |
| Dependency locking | `requirements.lock` without hashes, not used by CI | ⚠️ Partial — hashed lockfile planned |
| Third-party actions | Pinned by commit SHA (except `slsa-github-generator`, which requires a tag) | ✅ Implemented |

---

**Last reviewed:** 2026-10-24
**Maintainer:** [Arturo Gutierrez Rubio Rojas](mailto:agtzrubio@dagmalia.com)
**Organization:** [DAGMALIA — Governed, Observable & Declarative ML](https://dagmalia.com)
