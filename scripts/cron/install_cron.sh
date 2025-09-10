#!/usr/bin/env bash
set -euo pipefail
BEGIN="# BEGIN health_portal"
END="# END health_portal"
TMP="$(mktemp)"
crontab -l 2>/dev/null | awk -v b="$BEGIN" -v e="$END" '
  $0==b {skip=1}
  $0==e {skip=0; next}
  !skip {print}
' > "$TMP"
cat >> "$TMP" <<'CRON'
# BEGIN health_portal
8  2 * * * . /mnt/nas_storage/repos/health_portal/scripts/cron/env.sh && flock -n /tmp/hp_nightly.lock bash /mnt/nas_storage/repos/health_portal/scripts/cron/nightly.sh >> /mnt/nas_storage/repos/health_portal/cron.log 2>&1
20 2 * * * . /mnt/nas_storage/repos/health_portal/scripts/cron/env.sh && flock -n /tmp/hp_ai.lock python /mnt/nas_storage/repos/health_portal/jobs/ai_daily_scan.py --dsn "$HP_DSN" >> /mnt/nas_storage/repos/health_portal/cron.log 2>&1
0  3 * * * . /mnt/nas_storage/repos/health_portal/scripts/cron/env.sh && flock -n /tmp/hp_refresh_views.lock python /mnt/nas_storage/repos/health_portal/jobs/refresh_materialized_views.py --dsn "$HP_DSN" >> /mnt/nas_storage/repos/health_portal/cron.log 2>&1
30 3 * * * . /mnt/nas_storage/repos/health_portal/scripts/cron/env.sh && flock -n /tmp/hp_cleanup_sessions.lock python /mnt/nas_storage/repos/health_portal/jobs/cleanup_sessions.py --dsn "$HP_DSN" >> /mnt/nas_storage/repos/health_portal/cron.log 2>&1
# END health_portal
CRON
crontab "$TMP"
rm -f "$TMP"
echo "Installed cron entries."
