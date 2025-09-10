#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/psql.sh < init/040_views.sql
./scripts/psql.sh -c 'REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_daily_vitals;' || \
./scripts/psql.sh -c 'REFRESH MATERIALIZED VIEW analytics.mv_daily_vitals;'
echo "Views applied/refreshed."
