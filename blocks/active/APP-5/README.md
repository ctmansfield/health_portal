APP-5 — Sign-out flow & payload hashing

Scope
- Implement POST /reports/{id}/sign-out to finalize a report.
- Store payload hash (sha256) and signed_out_at; block subsequent mutations.

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- POST /reports/{id}/sign-out returns 200 with {id, signed_out_at, hash}.
- Re-issuing a signed report requires DB-2 policy paths (not in this block).

Touches
- srv/api/reports.py (sign-out handler)
- services/healthdb-pg-0001/migrations/* (if table changes are needed)
- tests/test_signout.py

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
