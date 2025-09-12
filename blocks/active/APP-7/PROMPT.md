You are working in the repository “health_portal”.

BLOCK
  ID: APP-7
  Title: Renderer snapshot tests (clinician & patient)
  Component: app
  State folder: blocks/active/APP-7/
  Closeout file (REQUIRED): blocks/active/APP-7/FINAL_SUMMARY.md

GOAL
  - Add HTML snapshot tests for clinician and patient views.
  - Stabilize templates with test IDs for consistent snapshots.

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - srv/api/templates/*.html
  - tests/test_snapshots.py

TESTS
  - Snapshots generated; update procedure documented (CI won’t fail on first create).

TECHNICAL NOTES
  - Ensure no PHI in stored snapshots (use synthetic data).

ACCEPTANCE CRITERIA
  - Snapshots pass locally; doc in README on how to update snapshots.

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c app-7/renderer-snapshot-tests-(clinician-&-patient)
  git add -A && git commit -m "APP-7: Renderer snapshot tests (clinician & patient)"
  git push -u origin app-7/renderer-snapshot-tests-(clinician-&-patient)
  gh pr create --title "APP-7: Renderer snapshot tests (clinician & patient)" \
               --body "See blocks/active/APP-7/FINAL_SUMMARY.md for details." \
               --base main --head app-7/renderer-snapshot-tests-(clinician-&-patient)

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/APP-7/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
