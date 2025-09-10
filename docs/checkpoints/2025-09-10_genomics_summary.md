Checkpoint: 2025-09-10 — Genomics summary materialized view

What I implemented
- Added a materialized view to summarize genomics reports for dashboard use:
  - services/healthdb-pg-0001/init/053_genomics_summary.sql
  - View: analytics.mv_genomics_summary (person_id, day, reports_count, summaries JSONB)
  - Index: idx_mv_genomics_summary_person_day

- Hooked the new materialized view into the nightly refresh job:
  - jobs/refresh_materialized_views.py: added "analytics.mv_genomics_summary" to VIEWS list so it will be refreshed by the existing cron job.

Why
- The new summary view provides a compact, fast-to-query summary of genomics reports per person/day for the dashboard, avoiding scans of the raw reports index on each request.

How to verify locally
1) Ensure DB migrations applied (already present in repo):
   bash scripts/db/apply_migrations.sh

2) Refresh materialized views (best-effort):
   . .venv/bin/activate && python jobs/refresh_materialized_views.py --dsn "$HP_DSN"

   Expected output (example):
   ('analytics.mv_daily_vitals', True, 'concurrent')
   ...
   ('analytics.mv_genomics_summary', True, 'concurrent'|'non-concurrent')

3) Query the view:
   psql "$HP_DSN" -c "select * from analytics.mv_genomics_summary limit 5;"

Notes / Next steps
- Seed or index genomics_reports (jobs/index_genomics_reports.py) so the view has rows; the seed job (jobs/seed_sample_data.py --genomics) can add sample rows for local dev.
- Consider adding a refresh schedule specifically for genomics if indexing is heavy; currently it is included in the nightly refresh pattern.

Files changed
- Added: services/healthdb-pg-0001/init/053_genomics_summary.sql
- Modified: jobs/refresh_materialized_views.py

Done by: LLM assistant (checkpoint) — 2025-09-10
