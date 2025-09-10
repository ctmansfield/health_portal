# DB-1 — Final Summary

This document summarizes the work performed for Block DB-1: "Baseline schema & views (report, variant, biomarker; report_exec_summary)" and contains instructions to verify and close the block.

Author: AI (database engineer assistant)
Date: 2025-09-10

---

## Goals
- Provide a minimal v1 baseline schema for clinician reports ensuring canonical JSONB payloads plus normalized tables for common queries.
- Add a view `analytics.report_exec_summary` that projects id, title, result, signed_out_at (normalized columns preferred, fallback to JSON payload).
- Provide migrations that apply and cleanly rollback.
- Provide CI verification (machine-readable JSON) and PR annotation for automated checks.

## Files added
- Migrations (apply + rollback + tests + verify script)
  - services/healthdb-pg-0001/migrations/001_report_baseline_up.sql
  - services/healthdb-pg-0001/migrations/001_report_baseline_down.sql
  - services/healthdb-pg-0001/migrations/002_report_baseline_test.sql
  - services/healthdb-pg-0001/migrations/verify_report_baseline.sh

- CI workflow
  - .github/workflows/db-report-verify.yml

- Contracts registry updated
  - core/contracts.yaml (db_schema_version: 1.1.0)

- Verify integration
  - VERIFY_ALL.sh (invokes verify script when HP_DSN set)

## Schema summary
- analytics.report
  - id uuid PK, report_id text unique, person_id text, title text, result text, payload jsonb, signed_out_at timestamptz, created_at timestamptz
  - Indexes: GIN on payload (jsonb_path_ops), B-tree on signed_out_at

- analytics.variant
  - id uuid PK, report_id uuid FK -> analytics.report(id) ON DELETE CASCADE, gene_symbol text, hgvs text, consequence text, allele_freq double precision, raw jsonb, created_at
  - Indexes: gene_symbol b-tree

- analytics.biomarker
  - id uuid PK, report_id uuid FK -> analytics.report(id) ON DELETE CASCADE, name, value_text, value_num, unit, raw jsonb, created_at
  - Indexes: name b-tree

- analytics.report_exec_summary (view)
  - Columns: id (text), title (text), result (text), signed_out_at (timestamptz)
  - Projects normalized columns first; falls back to payload fields: title, result, outcome, payload.summary.banner/result

## Verification and CI
- `verify_report_baseline.sh` performs the following steps (produces JSON output for CI):
  1. Applies 001_report_baseline_up.sql
  2. Runs 002_report_baseline_test.sql (asserts view exists and columns/types)
  3. Runs a smoke SELECT from analytics.report_exec_summary (returns up to 5 rows)
  4. Runs EXPLAIN ANALYZE for a variant gene filter
  5. Emits a JSON object to stdout with `status`, `message`, `smoke_sample`, and `explain` fields
  6. Rolls back by running 001_report_baseline_down.sql in a trap on exit

- CI workflow `.github/workflows/db-report-verify.yml`:
  - Triggers on PRs and pushes that touch services/healthdb-pg-0001/** or core/contracts.yaml
  - Starts a postgres:14 service, runs the verify script, uploads the `verify_report_results.json` artifact
  - Posts a PR comment summarizing results (Markdown table of sample rows + truncated EXPLAIN)

## How to run locally (recommended)
1. Start a disposable Postgres instance (docker is fine):
   docker run --rm -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:14
2. Export HP_DSN:
   export HP_DSN='postgresql://postgres:postgres@localhost:5432/postgres'
3. Run the verify script:
   ./services/healthdb-pg-0001/migrations/verify_report_baseline.sh | tee verify_report_results.json
4. Inspect `verify_report_results.json` for `status` and details.

## How to run in CI (already configured)
- Open a PR that modifies files under `services/healthdb-pg-0001/**` or `core/contracts.yaml`.
- The workflow `DB Report Baseline Verify` will run and comment on the PR.

## Rollback / cleanup
- The verify script automatically runs the down migration in a trap.
- To rollback manually:
  psql "$HP_DSN" -v ON_ERROR_STOP=1 -f services/healthdb-pg-0001/migrations/001_report_baseline_down.sql

## Notes and follow-ups
- I bumped core/contracts.yaml to 1.1.0 (MINOR) since we added new exported tables/views. Ensure required approvals per change_control before merging.
- The PR annotation attempts to link to the uploaded artifact (best-effort). If this is unreliable in your environment, we can embed the JSON content directly in the comment or upload to another storage.
- If you want a persistent migration history system (with down migrations in separate files and a migration table), we can integrate a migration tool (e.g., sqitch, alembic, migrate) later.

---

## Block close instructions (manual)
1. Stage and commit the files (if not already committed):
   git add services/healthdb-pg-0001/migrations/*.sql services/healthdb-pg-0001/migrations/verify_report_baseline.sh .github/workflows/db-report-verify.yml core/contracts.yaml VERIFY_ALL.sh
   git commit -m "DB-1: baseline report schema, view, tests, and CI verify workflow"

2. Run the project block close helper (if available):
   scripts/block/close_block.sh DB-1 "Add baseline report/variant/biomarker schema, report_exec_summary view, tests and CI verify workflow"

   If that script is not available, push branch and open a PR manually:
   git push --set-upstream origin <branch>
   gh pr create --title "DB-1: baseline report schema + verify CI" --body "Adds baseline report schema, view, tests, and CI verify workflow." --base main --head <branch>

---

End of summary.
