APP-1 — Ingest + JSON Schema validation

Scope
- Implement robust ingest for report payloads (HTTP + CLI).
- Validate against jsonschema; reject with detailed errors.
- Persist canonical JSON into analytics.report (payload, source, received_at).

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- POST /ingest/report validates and stores payload; returns new report id.
- CLI `python -m app.ingest <file.json>` supports local loading.
- Duplicate payloads are de-duplicated via hash.

Touches
- srv/api/genomics.py (or new ingest handler)
- app/reporting_scaffold/schemas/json/*.json (schema files)
- tests/test_ingest_validation.py

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
