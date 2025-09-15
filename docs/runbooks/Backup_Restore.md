# Runbook — Backup & Restore

Policy
- Daily logical backups (pg_dump) retained 14 days.
- Weekly base backups (pg_basebackup or volume snapshot) retained 8 weeks.
- Quarterly restore tests with documented RTO/RPO.

How To
- Backup now:
  - See scripts/cron/backup.sh
- Restore:
  - Provision target Postgres of compatible major version.
  - Restore weekly base, then apply daily logical backups if needed.
  - Run services/healthdb-pg-0001/scripts/refresh_views.sh.
  - Verify with services/healthdb-pg-0001/scripts/verify_report_baseline.sh.

Verification
- After restore, run: scripts/db/verify_counts.sql and UI smoke tests.

Details
- Daily at ~02:08 via cron (scripts/cron/nightly.sh triggers backup.sh)
- Keeps 14 most recent dumps at `/mnt/nas_storage/backups/health`
- Manual run: `bash scripts/cron/backup.sh`
- Restore example: `psql -h localhost -p 55432 -U health -d health -f /path/to/health_YYYY-MM-DD.sql`
