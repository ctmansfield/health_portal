APP-7 — Renderer snapshot tests (clinician & patient)

Scope
- Add HTML snapshot tests for clinician and patient views.
- Stabilize templates with test IDs for consistent snapshots.

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- Snapshots pass locally; doc in README on how to update snapshots.

Touches
- srv/api/templates/*.html
- tests/test_snapshots.py

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
