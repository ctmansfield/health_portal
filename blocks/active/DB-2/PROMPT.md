You are working in the repository “health_portal”.

BLOCK
  ID: DB-2
  Title: History & reissue policy tables
  Component: db
  State folder: blocks/active/DB-2/
  Closeout file (REQUIRED): blocks/active/DB-2/FINAL_SUMMARY.md

GOAL
  - Add analytics.report_history capturing previous payloads with cause and timestamp.
  - Add analytics.reissue_policy with rules (who/when/how) for APP-5+ flows.
  - Triggers to write history on update to analytics.report for unsigned reports only.

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - services/healthdb-pg-0001/migrations/*
  - services/healthdb-pg-0001/verify_report_baseline.sh (extend)

TESTS
  - psql-based migration tests; unit tests using dockerized Postgres (opt-in).

TECHNICAL NOTES
  - Keep JSONB path operations optimal; add compact GIN if needed.

ACCEPTANCE CRITERIA
  - Migrations apply/rollback cleanly; history rows appear on edit.

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c db-2/history-&-reissue-policy-tables
  git add -A && git commit -m "DB-2: History & reissue policy tables"
  git push -u origin db-2/history-&-reissue-policy-tables
  gh pr create --title "DB-2: History & reissue policy tables" \
               --body "See blocks/active/DB-2/FINAL_SUMMARY.md for details." \
               --base main --head db-2/history-&-reissue-policy-tables

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/DB-2/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
