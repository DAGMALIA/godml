# 🔐 GODML Security & Supply Chain Policy
# 🔐 GODML Security & Supply Chain Policy  
[![Supply Chain Verified](https://img.shields.io/badge/Supply%20Chain-Verified-brightgreen)](#)
[![SBOM SPDX](https://img.shields.io/badge/SBOM-SPDX-blue)](#)
[![SLSA Provenance](https://img.shields.io/badge/SLSA-v1-orange)](#)
[![Trusted Publisher](https://img.shields.io/badge/PyPI-Trusted%20Publisher-purple)](#)


## 🧱 Overview

GODML follows a **secure-by-default** and **supply chain–verified** approach to software delivery.  
All code, dependencies, and build artifacts are validated, signed, and published through a fully auditable CI/CD pipeline.

The release workflow includes:
- **Static analysis** (Bandit) for code-level security.
- **Dependency vulnerability scanning** (Safety).
- **Software Bill of Materials (SBOM)** generation in SPDX format.
- **Provenance and attestation** using [SLSA v1](https://slsa.dev/spec/v1.0) and [Sigstore Cosign](https://docs.sigstore.dev/).
- **Trusted publishing** to PyPI using OIDC authentication.

---

## 🧩 Security Principles

1. **Defense in Depth** — Multi-layered validation from source to artifact.  
2. **Zero Trust Builds** — All workflows are isolated and use ephemeral GitHub-hosted runners.  
3. **Keyless Signing** — Every release artifact is signed via OIDC tokens and verified by Cosign.  
4. **Secure by Default** — No service binds externally unless explicitly configured.  
5. **Transparency** — All security exceptions and mitigations are traceable in CI logs and this document.

---

## 🧪 Security Scans

| Tool | Purpose | Enforcement |
|------|----------|-------------|
| **Bandit** | Detects insecure code patterns (e.g., hardcoded secrets, unsafe bindings) | Required |
| **Safety** | Detects dependency CVEs | Required (with documented exceptions) |
| **Anchore SBOM** | Generates SPDX-compliant dependency inventory | Required |
| **Cosign** | Signs artifacts and provenance | Required |
| **SLSA Provenance** | Ensures build integrity and auditability | Required |

Reports are attached as pipeline artifacts under the job:  
**“🔐 GODML Supply Chain + PyPI Release”**.

---

## 🧾 Known Vulnerabilities & Accepted Risks

As of **v1.0.0**, GODML uses `mlflow==3.4.0`, which has 8 reported vulnerabilities without available fixes.

**Justification and mitigation:**
- Vulnerabilities have **no known exploit path** within GODML’s runtime context.
- GODML executes within **isolated CI/CD containers** and **private network scopes**.
- Dependencies are **pinned and hash-verified** via `requirements.lock`.
- Continuous monitoring in [Safety Platform](https://platform.safetycli.com/codebases/godml/findings?branch=main).
- Risk is **formally accepted under supply chain policy** and documented in CI logs as:

::notice::Residual risk: MLflow 3.4.0 vulnerabilities documented and accepted under supply chain policy

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
|------------|----------|---------|
| Code signing | Sigstore (OIDC keyless) | ✅ Implemented |
| Dependency locking | `requirements.lock` with hashes | ✅ Implemented |
| SBOM tracking | SPDX JSON format | ✅ Implemented |
| Provenance (SLSA) | v1 provenance document signed | ✅ Implemented |
| Vulnerability policy | Safety scan + risk justification | ✅ Implemented |
| PyPI publishing | Trusted Publisher (OIDC) | ✅ Implemented |

---

**Last reviewed:** 2025-10-14  
**Maintainer:** [Arturo Gutierrez Rubio Rojas](mailto:agtzrubio@dagmalia.com)  
**Organization:** [DAGMALIA — Governed, Observable & Declarative ML](https://dagmalia.com)

## ⚠️ Vulnerabilidades conocidas ignoradas temporalmente

Actualmente, el paquete `mlflow==3.4.0` contiene las siguientes vulnerabilidades no parchadas oficialmente:

- 71577, 71578, 71579, 71584, 71587, 71691, 71692, 71693

Estas han sido marcadas como `ignored` en nuestra política debido a que:

- No existe aún una versión segura publicada.
- No se cargan modelos de fuentes externas (RCE mitigado).
- Se monitorea semanalmente su estado vía Safety CLI.

Ver: https://data.safetycli.com/p/pypi/mlflow/eda/?from=3.4.0
