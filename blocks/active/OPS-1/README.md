OPS-1 — VERIFY_ALL end-to-end checks (local)

Scope
- Provide a single runner script to verify DB migrations, API routes, and UI smoke (headless).
- Emit concise pass/fail summary; optional Dockerized Postgres/Redis.

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- One-command local verification documented in README.

Touches
- scripts/verify_all.sh
- docs/architecture/Runbooks/Reissue_Workflow.md (link in output)

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
