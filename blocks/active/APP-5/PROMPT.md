You are working in the repository “health_portal”.

BLOCK
  ID: APP-5
  Title: Sign-out flow & payload hashing
  Component: app
  State folder: blocks/active/APP-5/
  Closeout file (REQUIRED): blocks/active/APP-5/FINAL_SUMMARY.md

GOAL
  - Implement POST /reports/{id}/sign-out to finalize a report.
  - Store payload hash (sha256) and signed_out_at; block subsequent mutations.

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - srv/api/reports.py (sign-out handler)
  - services/healthdb-pg-0001/migrations/* (if table changes are needed)
  - tests/test_signout.py

TESTS
  - Hash is stable for same payload; sign-out is idempotent.
  - Further writes/mods rejected with 409.

TECHNICAL NOTES
  - Audit log new row (who, when, ip if available).

ACCEPTANCE CRITERIA
  - POST /reports/{id}/sign-out returns 200 with {id, signed_out_at, hash}.
  - Re-issuing a signed report requires DB-2 policy paths (not in this block).

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c app-5/sign-out-flow-&-payload-hashing
  git add -A && git commit -m "APP-5: Sign-out flow & payload hashing"
  git push -u origin app-5/sign-out-flow-&-payload-hashing
  gh pr create --title "APP-5: Sign-out flow & payload hashing" \
               --body "See blocks/active/APP-5/FINAL_SUMMARY.md for details." \
               --base main --head app-5/sign-out-flow-&-payload-hashing

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/APP-5/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
