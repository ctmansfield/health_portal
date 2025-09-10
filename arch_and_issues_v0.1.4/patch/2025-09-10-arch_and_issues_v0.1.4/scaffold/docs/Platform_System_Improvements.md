# Platform & System Improvements — Recommendations & Priorities

**NOW**
1) Contracts in CI — validate `core/contracts.yaml` and fail on drift.
2) Schema validation on ingest (jsonschema).
3) OpenAPI guardrails & client generation for dashboard.
4) RBAC & tokens; PHI-safe logging defaults.
5) Renderer snapshot tests; patient-mode reading-level check.
6) Alembic migrations with up/down tests.
7) Observability baseline (logs + metrics).
8) Pick PDF engine; lock fonts & print CSS tests.

**NEXT**
1) Cache summaries and patient HTML.
2) Async jobs for PDF & FHIR export.
3) Feature flags & theme tokens per tenant.
4) Full OpenTelemetry tracing; SLO dashboards.
5) SNOMED ↔ ICD-10-CM concept maps (scaffold tables).

**LATER**
1) Trial matcher plugin.
2) GA4GH VRS normalization.
3) PGx cards.
4) Warehouse taps + dbt models.
5) ABAC & row-level security for multi-tenant.

**Acceptance**: Each item has a DoD and issue ID.
