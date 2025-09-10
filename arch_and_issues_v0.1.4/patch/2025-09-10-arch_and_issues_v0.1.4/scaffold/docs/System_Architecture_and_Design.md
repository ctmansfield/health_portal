# System Architecture & Design — Health Portal (v0.1.x)

This captures the current repo layout and the **target** architecture for genomics reporting, with evaluation and recommendations.

## 1) Repository Snapshot (observed)
- Top-level: `app/`, `docs/`, `jobs/`, `patch/`, `scripts/`, `services/healthdb-pg-0001/`, `srv/`, `tests/`, `tools/`.
- Primary language: Python. Pre-commit + Makefile present; `verify.sh` exists.

## 2) Target Architecture
See `diagrams/architecture.mmd` (Mermaid). Components:
- **Dashboard** (frontend): clinician summary card, full report view, patient-facing view. Consumes the API.
- **Application Layer**: OpenAPI (read-only v1), renderer, FHIR/VRS exporters, sign-out & hashing, ingest validation.
- **Database**: JSONB canonical payload + normalized tables (report, variant, biomarker) and views.
- **Pipelines (genomics_stack)**: emit canonical `report.v1.json`; provenance into Methods/QC.

## 3) Interfaces & Contracts (stable v1.0.0)
- **DB schema**: `report`, `variant`, `biomarker`; views including `report_exec_summary`.
- **API**: `GET /reports/{id}`, `GET /reports/{id}/summary`, `GET /reports/{id}/patient`.
- **Payload schemas**: `report.v1.json`, `variant.v1.json`, `biomarker.v1.json`, `codes.v1.json`.

## 4) Security & Compliance
Least-privilege DB roles; PHI-safe logging; payload hashing at sign-out; environment segregation; synthetic data in staging.

## 5) Observability
Metrics (imports, render time, API latency), tracing (OpenTelemetry), JSON logs with correlation ids.

## 6) Deployment
Patch-style installers & verifiers; idempotent migrations; rollback; CI gates for schemas and OpenAPI.

## 7) Risks
Renderer bottleneck; schema drift; API version negotiation; PDF fidelity risk.

## 8) Recommendations (see separate doc for priorities)
- Enforce schema validation on ingest; OpenAPI lint; Alembic migrations; OpenTelemetry; choose PDF engine; RBAC; feature flags; concept maps; VERIFY_ALL.sh.
