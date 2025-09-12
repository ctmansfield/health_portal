You are working in the repository “health_portal”.

BLOCK
  ID: APP-6
  Title: FHIR/VRS exporters (stubs)
  Component: app
  State folder: blocks/active/APP-6/
  Closeout file (REQUIRED): blocks/active/APP-6/FINAL_SUMMARY.md

GOAL
  - Create minimal exporters for clinician payload: FHIR DiagnosticReport, GA4GH VRS stub.
  - Add GET /reports/{id}/fhir and /reports/{id}/vrs.

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - srv/api/reports.py (exporters)
  - api/openapi.genomics_reports.v1.yaml
  - tests/test_exports.py

TESTS
  - FHIR JSON validates against minimal profile subset (use small jsonschema).
  - VRS stub contains placeholder identifiers and example alleles.

TECHNICAL NOTES
  - Make exporters pure functions for future reuse.

ACCEPTANCE CRITERIA
  - Endpoints present and return JSON; documented in OpenAPI.

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c app-6/fhir-vrs-exporters-(stubs)
  git add -A && git commit -m "APP-6: FHIR/VRS exporters (stubs)"
  git push -u origin app-6/fhir-vrs-exporters-(stubs)
  gh pr create --title "APP-6: FHIR/VRS exporters (stubs)" \
               --body "See blocks/active/APP-6/FINAL_SUMMARY.md for details." \
               --base main --head app-6/fhir-vrs-exporters-(stubs)

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/APP-6/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
