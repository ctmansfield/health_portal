You are working in the repository “health_portal”.

BLOCK
  ID: APP-1
  Title: Ingest + JSON Schema validation
  Component: app
  State folder: blocks/active/APP-1/
  Closeout file (REQUIRED): blocks/active/APP-1/FINAL_SUMMARY.md

GOAL
  - Implement robust ingest for report payloads (HTTP + CLI).
  - Validate against jsonschema; reject with detailed errors.
  - Persist canonical JSON into analytics.report (payload, source, received_at).

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - srv/api/genomics.py (or new ingest handler)
  - app/reporting_scaffold/schemas/json/*.json (schema files)
  - tests/test_ingest_validation.py

TESTS
  - Schema happy-path and failing samples (invalid types, missing fields).
  - DB insertion verified; idempotency via payload hash (no duplicates).

TECHNICAL NOTES
  - Return 400 with machine-readable error list (path, message, offending value).
  - Compute SHA-256 digest of payload for idempotency; store in analytics.report.hash.

ACCEPTANCE CRITERIA
  - POST /ingest/report validates and stores payload; returns new report id.
  - CLI `python -m app.ingest <file.json>` supports local loading.
  - Duplicate payloads are de-duplicated via hash.

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c app-1/ingest-+-json-schema-validation
  git add -A && git commit -m "APP-1: Ingest + JSON Schema validation"
  git push -u origin app-1/ingest-+-json-schema-validation
  gh pr create --title "APP-1: Ingest + JSON Schema validation" \
               --body "See blocks/active/APP-1/FINAL_SUMMARY.md for details." \
               --base main --head app-1/ingest-+-json-schema-validation

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/APP-1/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
