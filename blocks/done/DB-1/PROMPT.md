You are implementing **DB-1: DB-1** for component **n/a**.

Context
- Dependencies: —
- Interfaces:
  - - View: `analytics.report_exec_summary(id,title,result,signed_out_at)`
  - - Tables: `analytics.report`, `analytics.variant`, `analytics.biomarker`
- Acceptance:
  - (none)
- Touch points: (none)

Tasks
1) Implement per the interfaces above. Keep payloads stable and auth enforced.
2) Add/update tests for the changed components.
3) Ensure no PHI is logged; prefer structured logs.
4) Update OpenAPI or DB migrations when applicable.

Definition of Done
- (none)

Run & Verify (local)
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
