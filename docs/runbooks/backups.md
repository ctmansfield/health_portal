# Backups
- Daily at ~02:08 via cron.
- Keeps 14 most recent dumps at `/mnt/nas_storage/backups/health`.
- Manual run: `bash scripts/cron/backup.sh`
- Restore example: `psql -h localhost -p 55432 -U health -d health -f /path/to/health_YYYY-MM-DD.sql`
