APP-6 — FHIR/VRS exporters (stubs)

Scope
- Create minimal exporters for clinician payload: FHIR DiagnosticReport, GA4GH VRS stub.
- Add GET /reports/{id}/fhir and /reports/{id}/vrs.

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- Endpoints present and return JSON; documented in OpenAPI.

Touches
- srv/api/reports.py (exporters)
- api/openapi.genomics_reports.v1.yaml
- tests/test_exports.py

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
