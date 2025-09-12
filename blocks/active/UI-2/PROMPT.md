You are working in the repository “health_portal”.

BLOCK
  ID: UI-2
  Title: Full clinician report view
  Component: ui
  State folder: blocks/active/UI-2/
  Closeout file (REQUIRED): blocks/active/UI-2/FINAL_SUMMARY.md

GOAL
  - Render full clinician report from canonical payload with sticky TOC.
  - Deep-linkable sections and share-safe anchors (no PHI in URL).

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - srv/api/templates/genomics_report.html
  - srv/api/static/style.css

TESTS
  - tests/test_ui_integration.py — presence of sections, TOC anchors.

TECHNICAL NOTES
  - Do not over-fetch; reuse /reports/{id}.

ACCEPTANCE CRITERIA
  - Loads quickly; sections navigable; a11y passes basic checks.

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c ui-2/full-clinician-report-view
  git add -A && git commit -m "UI-2: Full clinician report view"
  git push -u origin ui-2/full-clinician-report-view
  gh pr create --title "UI-2: Full clinician report view" \
               --body "See blocks/active/UI-2/FINAL_SUMMARY.md for details." \
               --base main --head ui-2/full-clinician-report-view

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/UI-2/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
