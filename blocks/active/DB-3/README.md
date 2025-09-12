DB-3 — Indexing strategy (geneSymbol; signOut.date)

Scope
- Add indexes: gene symbols within payload (jsonb_path_ops), signed_out_at date, and common filters.
- EXPLAIN demonstrates improved plans for typical queries.

Interfaces / Contracts
- Keep API versioning under api/openapi.genomics_reports.v1.yaml when applicable.
- Respect DB schemas and views under services/healthdb-pg-0001/.
- UI follows UI-6 responsive grid and a11y checklist.

Acceptance
- Measured query time improvement (>30% on target queries).

Touches
- services/healthdb-pg-0001/migrations/*

Run / Verify
- . .venv/bin/activate
- pytest -q
- uvicorn srv.api.main:app --reload
