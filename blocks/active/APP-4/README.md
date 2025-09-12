APP-4 — Patient-mode endpoint

Scope
- Create patient-safe summary (no sensitive clinician fields).
- Implement GET /reports/{id}/patient returning summarized payload.

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- 200 returns patient-safe JSON matching schema (document in OpenAPI v1).
- 404 for missing id; 400 for invalid id format.

Touches
- srv/api/reports.py (patient handler)
- docs/architecture/ADRs/ADR-0004-Patient_Mode_Summarization.md
- tests/test_patient_mode.py

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
