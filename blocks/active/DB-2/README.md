DB-2 — History & reissue policy tables

Scope
- Add analytics.report_history capturing previous payloads with cause and timestamp.
- Add analytics.reissue_policy with rules (who/when/how) for APP-5+ flows.
- Triggers to write history on update to analytics.report for unsigned reports only.

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- Migrations apply/rollback cleanly; history rows appear on edit.

Touches
- services/healthdb-pg-0001/migrations/*
- services/healthdb-pg-0001/verify_report_baseline.sh (extend)

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
