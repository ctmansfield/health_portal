You are working in the repository “health_portal”.

BLOCK
  ID: APP-4
  Title: Patient-mode endpoint
  Component: app
  State folder: blocks/active/APP-4/
  Closeout file (REQUIRED): blocks/active/APP-4/FINAL_SUMMARY.md

GOAL
  - Create patient-safe summary (no sensitive clinician fields).
  - Implement GET /reports/{id}/patient returning summarized payload.

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - srv/api/reports.py (patient handler)
  - docs/architecture/ADRs/ADR-0004-Patient_Mode_Summarization.md
  - tests/test_patient_mode.py

TESTS
  - Ensure restricted fields are excluded (variants with sensitive annotations).
  - Read from canonical payload; no DB writes.

TECHNICAL NOTES
  - Follow ADR-0004 redaction rules and tone for consumer comprehension.
  - Include explanation strings and references (plain language).

ACCEPTANCE CRITERIA
  - 200 returns patient-safe JSON matching schema (document in OpenAPI v1).
  - 404 for missing id; 400 for invalid id format.

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c app-4/patient-mode-endpoint
  git add -A && git commit -m "APP-4: Patient-mode endpoint"
  git push -u origin app-4/patient-mode-endpoint
  gh pr create --title "APP-4: Patient-mode endpoint" \
               --body "See blocks/active/APP-4/FINAL_SUMMARY.md for details." \
               --base main --head app-4/patient-mode-endpoint

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/APP-4/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
