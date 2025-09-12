You are working in the repository “health_portal”.

BLOCK
  ID: OPS-1
  Title: VERIFY_ALL end-to-end checks (local)
  Component: ops
  State folder: blocks/active/OPS-1/
  Closeout file (REQUIRED): blocks/active/OPS-1/FINAL_SUMMARY.md

GOAL
  - Provide a single runner script to verify DB migrations, API routes, and UI smoke (headless).
  - Emit concise pass/fail summary; optional Dockerized Postgres/Redis.

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - scripts/verify_all.sh
  - docs/architecture/Runbooks/Reissue_Workflow.md (link in output)

TESTS
  - CI-skippable; local use only but returns nonzero on failure.

TECHNICAL NOTES
  - Don’t hard fail if Docker missing; degrade gracefully.

ACCEPTANCE CRITERIA
  - One-command local verification documented in README.

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c ops-1/verify_all-end-to-end-checks-(local)
  git add -A && git commit -m "OPS-1: VERIFY_ALL end-to-end checks (local)"
  git push -u origin ops-1/verify_all-end-to-end-checks-(local)
  gh pr create --title "OPS-1: VERIFY_ALL end-to-end checks (local)" \
               --body "See blocks/active/OPS-1/FINAL_SUMMARY.md for details." \
               --base main --head ops-1/verify_all-end-to-end-checks-(local)

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/OPS-1/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
