You are working in the repository “health_portal”.

BLOCK
  ID: UI-3
  Title: Patient-mode view & PDF
  Component: ui
  State folder: blocks/active/UI-3/
  Closeout file (REQUIRED): blocks/active/UI-3/FINAL_SUMMARY.md

GOAL
  - Create simplified patient view for /reports/{id}/patient (APP-4).
  - Provide PDF export (headless Chrome or WeasyPrint) with consistent pagination.

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - srv/api/templates/patient_report.html
  - srv/api/genomics.py (PDF route or background job stub)

TESTS
  - tests/test_ui_patient_pdf.py (smoke) and DOM presence.

TECHNICAL NOTES
  - Ensure fonts are embedded; no external calls in PDF renderer.

ACCEPTANCE CRITERIA
  - HTML patient view accessible; PDF export works locally.

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c ui-3/patient-mode-view-&-pdf
  git add -A && git commit -m "UI-3: Patient-mode view & PDF"
  git push -u origin ui-3/patient-mode-view-&-pdf
  gh pr create --title "UI-3: Patient-mode view & PDF" \
               --body "See blocks/active/UI-3/FINAL_SUMMARY.md for details." \
               --base main --head ui-3/patient-mode-view-&-pdf

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/UI-3/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
