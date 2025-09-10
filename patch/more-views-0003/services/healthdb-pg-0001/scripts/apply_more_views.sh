#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/psql.sh < init/047_more_vitals_views.sql
# Refresh newly added MV (concurrently if unique key exists later)
./scripts/psql.sh -c "REFRESH MATERIALIZED VIEW analytics.mv_weight_daily;"
echo "More vitals views applied."
