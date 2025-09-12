UI-2 — Full clinician report view

Scope
- Render full clinician report from canonical payload with sticky TOC.
- Deep-linkable sections and share-safe anchors (no PHI in URL).

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- Loads quickly; sections navigable; a11y passes basic checks.

Touches
- srv/api/templates/genomics_report.html
- srv/api/static/style.css

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
