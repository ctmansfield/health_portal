Checkpoint: 2025-09-10 — Seed migration, indexes, and dedicated genomics refresh cron

What I implemented in this block:

1) Deterministic SQL seed migration
- services/healthdb-pg-0001/init/054_seed_demo.sql
  - Inserts 30 days of deterministic demo events into analytics.data_events for person_id 'me'
  - Inserts 10 demo analytics.genomics_reports rows with predictable report_id/path/summary
  - Inserts 14 demo analytics.ai_findings rows
  - Adds an index on mv_genomics_summary.day if the view exists

2) Additional indexes for the genomics summary
- services/healthdb-pg-0001/init/055_genomics_summary_indexes.sql
  - Adds indexes on analytics.mv_genomics_summary(person_id, day) and a GIN index on summaries jsonb for faster JSON lookups

3) Dedicated refresh job and cron entry
- jobs/refresh_genomics_summary.py — refreshes analytics.mv_genomics_summary (CONCURRENTLY where possible)
- scripts/cron/install_cron.sh — added a cron entry (0 4 * * *) to run the genomics refresh daily under flock locking

4) Updated nightly refresh to include mv_genomics_summary (jobs/refresh_materialized_views.py)

How to verify locally (recommended order):
1. Ensure DB is up and HP_DSN is set
   export HP_DSN="postgresql://health:health_pw@localhost:55432/health"

2. Apply migrations (this will create the new seed migration as well):
   bash scripts/db/apply_migrations.sh

3. Seed demo data (SQL seed is included in migrations, so it was already applied; if you prefer to re-run the Python seeder you can):
   . .venv/bin/activate
   python jobs/seed_sample_data.py --dsn "$HP_DSN" --genomics --findings --days 30

4. Refresh materialized views (or wait for cron):
   python jobs/refresh_materialized_views.py --dsn "$HP_DSN"
   # or refresh only genomics summary
   python jobs/refresh_genomics_summary.py --dsn "$HP_DSN"

5. Query results:
   psql "$HP_DSN" -c "SELECT count(*) FROM analytics.data_events;"
   psql "$HP_DSN" -c "SELECT count(*) FROM analytics.genomics_reports;"
   psql "$HP_DSN" -c "SELECT * FROM analytics.mv_genomics_summary LIMIT 5;"

6. Confirm cron entry (if you installed via scripts/cron/install_cron.sh):
   crontab -l | grep hp_genomics_refresh

Notes / Caveats:
- The seed migration (054) is idempotent (uses ON CONFLICT DO NOTHING) so it is safe to re-apply.
- The GIN index on summaries can increase space usage; consider it optional depending on query patterns.
- The dedicated genomics refresh cron runs at 04:00 by default to reduce contention with other nightly jobs.

Files added/modified:
- Added: services/healthdb-pg-0001/init/054_seed_demo.sql
- Added: services/healthdb-pg-0001/init/055_genomics_summary_indexes.sql
- Added: jobs/refresh_genomics_summary.py
- Modified: scripts/cron/install_cron.sh (added cron line)
- Modified: jobs/refresh_materialized_views.py (added analytics.mv_genomics_summary earlier)

Done by: LLM assistant (checkpoint) — 2025-09-10
