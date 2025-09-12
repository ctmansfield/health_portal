You are working in the repository “health_portal”.

BLOCK
  ID: DB-3
  Title: Indexing strategy (geneSymbol; signOut.date)
  Component: db
  State folder: blocks/active/DB-3/
  Closeout file (REQUIRED): blocks/active/DB-3/FINAL_SUMMARY.md

GOAL
  - Add indexes: gene symbols within payload (jsonb_path_ops), signed_out_at date, and common filters.
  - EXPLAIN demonstrates improved plans for typical queries.

KEY CONTEXT
  • Existing endpoints & conventions to respect:
    - /reports/{id} (clinician payload) and /reports/{id}/summary
    - Labs critical-series API & Redis cache (app/hp_etl/cache.py), UI-6 responsive grid
    - ADRs under docs/architecture/ADRs/
  • You MUST avoid logging PHI/PII; prefer structured logs without identifiers.
  • Performance: keep handlers O(#rows returned), use DB indexes; prefer cache if available.

FILES YOU WILL TOUCH (typical)
  - services/healthdb-pg-0001/migrations/*

TESTS
  - Explain plan comparisons captured in docs/architecture/PERF_NOTES.md (append).

TECHNICAL NOTES
  - Consider partial indexes where NULLS are common.

ACCEPTANCE CRITERIA
  - Measured query time improvement (>30% on target queries).

RUN / VERIFY LOCALLY
  . .venv/bin/activate
  pytest -q
  uvicorn srv.api.main:app --reload

GIT / PR (from terminal)
  git switch -c db-3/indexing-strategy-(genesymbol;-signout.date)
  git add -A && git commit -m "DB-3: Indexing strategy (geneSymbol; signOut.date)"
  git push -u origin db-3/indexing-strategy-(genesymbol;-signout.date)
  gh pr create --title "DB-3: Indexing strategy (geneSymbol; signOut.date)" \
               --body "See blocks/active/DB-3/FINAL_SUMMARY.md for details." \
               --base main --head db-3/indexing-strategy-(genesymbol;-signout.date)

WHEN DONE — WRITE CLOSEOUT
  Complete blocks/active/DB-3/FINAL_SUMMARY.md with:
    - What changed (files/functions)
    - Interfaces (routes/SQL/DOM; sample requests/responses)
    - Tests and how to run
    - Verification steps (URLs, screenshots ok)
    - Risks/follow-ups
    - Ops notes (migrations, env vars, TTLs)
