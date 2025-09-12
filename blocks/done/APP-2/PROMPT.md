You are implementing **APP-2: APP-2** for component **n/a**.

Context
- Dependencies: —
- Interfaces:
  - - **GET /reports/{id}** → returns canonical JSON stored in `analytics.report.payload`.
  - - OpenAPI: `api/openapi.genomics_reports.v1.yaml`
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
