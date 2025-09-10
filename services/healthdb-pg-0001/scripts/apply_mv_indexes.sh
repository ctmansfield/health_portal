#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Ensure the SQL exists; apply it
./scripts/psql.sh < init/046_mv_unique_indexes.sql
# Try concurrent refresh now that unique keys exist (fallback non-concurrent)
for mv in analytics.mv_events_daily analytics.mv_vitals_daily_wide analytics.mv_daily_vitals; do
  ./scripts/psql.sh -c "REFRESH MATERIALIZED VIEW CONCURRENTLY $mv;" \
  || ./scripts/psql.sh -c "REFRESH MATERIALIZED VIEW $mv;"
done
echo "MV indexes applied & refreshed."
