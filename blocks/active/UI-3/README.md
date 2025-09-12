UI-3 — Patient-mode view & PDF

Scope
- Create simplified patient view for /reports/{id}/patient (APP-4).
- Provide PDF export (headless Chrome or WeasyPrint) with consistent pagination.

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- HTML patient view accessible; PDF export works locally.

Touches
- srv/api/templates/patient_report.html
- srv/api/genomics.py (PDF route or background job stub)

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
