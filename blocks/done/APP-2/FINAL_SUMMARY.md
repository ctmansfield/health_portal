# APP-2 — Final Summary: GET /reports/{id}

This document summarizes the APP-2 implementation: a read-only endpoint that returns the canonical clinician report payload exactly as stored in the database.

Files added/modified
- Added API contract (OpenAPI v1):
  - api/openapi.genomics_reports.v1.yaml
- Added application handler (FastAPI router) and registration:
  - srv/api/reports.py
  - srv/api/main.py (includes reports router)
- Tests:
  - tests/test_app_reports.py
- Block documentation:
  - blocks/active/APP-2/FINAL_SUMMARY.md (this file)

Endpoint implemented
- GET /reports/{id}
  - Accepts: path param id (UUID)
  - Behavior:
    - Validates id as UUID — returns 400 for invalid format
    - Queries analytics.report by id (UUID) and returns payload JSONB verbatim
    - Returns 404 if not found
    - Response headers include:
      - Content-Type: application/json; charset=utf-8
      - Cache-Control: no-store

Sample curl (success)

curl -v -X GET "http://localhost:8000/reports/11111111-2222-3333-4444-555555555555" \
  -H 'Accept: application/json'

Success (200) example body (exactly the payload JSON stored in DB):

{
  "report": "ok",
  "value": 123
}

Not found (404) example body:

{
  "detail": "Report not found"
}

Invalid id (400) example body:

{
  "detail": "invalid id format"
}

How to run tests locally

1. Install dev dependencies (pytest, fastapi, httpx testclient) if not present.
2. Run pytest (these are unit tests using monkeypatch to avoid hitting a real DB):

pytest tests/test_app_reports.py -q

Notes
- The endpoint reads from analytics.report(id) and returns the payload column "as-is" as a JSON object.
- No transformation, trimming, or sanitization is performed beyond returning the payload and adding the Cache-Control header to discourage caching of PHI.
- This block intentionally does not implement /reports/{id}/summary; that is APP-3.

If you want any adjustments (e.g., different cache header, content disposition, or additional logging), tell me and I will update the implementation.
