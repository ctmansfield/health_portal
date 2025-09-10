#!/usr/bin/env bash
set -euo pipefail
# Environment
. /mnt/nas_storage/repos/health_portal/scripts/cron/env.sh

# 1) Refresh materialized views
/mnt/nas_storage/repos/health_portal/services/healthdb-pg-0001/scripts/apply_views.sh

# 2) (Optional) run AI scan as part of nightly too (cron also runs it at 02:20)
/usr/bin/env python /mnt/nas_storage/repos/health_portal/jobs/ai_daily_scan.py --dsn "${HP_DSN}"

echo "$(date -Is) nightly done"
