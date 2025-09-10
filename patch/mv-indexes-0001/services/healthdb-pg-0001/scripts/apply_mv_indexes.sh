#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/psql.sh < init/046_mv_unique_indexes.sql
# try concurrent now that unique keys exist
for mv in analytics.mv_events_daily analytics.mv_vitals_daily_wide analytics.mv_daily_vitals; do
  ./scripts/psql.sh -c "REFRESH MATERIALIZED VIEW CONCURRENTLY $mv;" \
  || ./scripts/psql.sh -c "REFRESH MATERIALIZED VIEW $mv;"
done
echo "MV indexes applied & refreshed."
